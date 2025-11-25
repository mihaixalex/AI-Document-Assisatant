// app/api/ingest/route.ts
import { indexConfig } from '@/constants/graphConfigs';
import { NextRequest, NextResponse } from 'next/server';
import http from 'http';
import https from 'https';

export const runtime = 'nodejs';

// Create HTTP agents that force IPv4
const httpAgent = new http.Agent({
  family: 4, // Force IPv4
  keepAlive: true,
});

const httpsAgent = new https.Agent({
  family: 4, // Force IPv4
  keepAlive: true,
});

// Configuration constants
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_FILE_TYPES = ['application/pdf'];

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const files: File[] = [];

    // Get threadId from formData
    const threadId = formData.get('threadId') as string;
    if (!threadId || threadId.trim() === '') {
      return NextResponse.json(
        { error: 'Thread ID is required' },
        { status: 400 }
      );
    }

    // Get isShared flag (defaults to false) - strict boolean validation
    const isSharedStr = formData.get('isShared');
    const isShared = isSharedStr !== null && isSharedStr === 'true';

    for (const [key, value] of formData.entries()) {
      // Check if it's a File by checking for File-like properties
      if (key === 'files' && typeof value === 'object' && value !== null && 'name' in value && 'type' in value) {
        files.push(value as File);
      }
    }

    if (!files || files.length === 0) {
      return NextResponse.json({ error: 'No files provided' }, { status: 400 });
    }

    // Validate file count
    if (files.length > 5) {
      return NextResponse.json(
        { error: 'Too many files. Maximum 5 files allowed.' },
        { status: 400 },
      );
    }

    // Validate file types and sizes
    const invalidFiles = files.filter((file) => {
      return (
        !ALLOWED_FILE_TYPES.includes(file.type) || file.size > MAX_FILE_SIZE
      );
    });

    if (invalidFiles.length > 0) {
      return NextResponse.json(
        {
          error:
            'Only PDF files are allowed and file size must be less than 10MB',
        },
        { status: 400 },
      );
    }

    const fastApiUrl =
      process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    // Process each file and send to FastAPI
    const results = [];
    for (const file of files) {
      try {
        // Create FormData for FastAPI request
        const fastapiFormData = new FormData();
        fastapiFormData.append('file', file);
        fastapiFormData.append('threadId', threadId);
        fastapiFormData.append('config', JSON.stringify({
          configurable: {
            ...indexConfig,
            thread_id: threadId,
            is_shared: isShared, // Pass shared KB flag to backend
          },
        }));

        // Send to FastAPI backend with IPv4-only agent
        const response = await fetch(`${fastApiUrl}/api/ingest`, {
          method: 'POST',
          body: fastapiFormData,
          // @ts-ignore - agent option exists but not in types
          agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          console.error(`Error ingesting ${file.name}:`, errorData);
          results.push({
            file: file.name,
            status: 'error',
            error: errorData.detail || 'Ingestion failed',
          });
        } else {
          const resultData = await response.json();
          results.push({
            file: file.name,
            status: 'success',
            threadId: resultData.threadId,
          });
        }
      } catch (error: any) {
        console.error(`Error processing file ${file.name}:`, error);
        results.push({
          file: file.name,
          status: 'error',
          error: error.message || 'Unknown error',
        });
      }
    }

    // Check if any succeeded
    const successCount = results.filter((r) => r.status === 'success').length;

    if (successCount === 0) {
      return NextResponse.json(
        { error: 'Failed to ingest any documents', results },
        { status: 500 },
      );
    }

    return NextResponse.json({
      message: `Successfully ingested ${successCount} of ${files.length} documents`,
      results,
    });
  } catch (error: any) {
    console.error('Error processing files:', error);
    return NextResponse.json(
      { error: 'Failed to process files', details: error.message },
      { status: 500 },
    );
  }
}
