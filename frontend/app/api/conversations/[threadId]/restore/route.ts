// app/api/conversations/[threadId]/restore/route.ts
import { NextRequest, NextResponse } from 'next/server';
import http from 'http';
import https from 'https';

export const runtime = 'nodejs';

// Create HTTP agents that force IPv4
const httpAgent = new http.Agent({
  family: 4,
  keepAlive: true,
});

const httpsAgent = new https.Agent({
  family: 4,
  keepAlive: true,
});

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ threadId: string }> }
) {
  try {
    const { threadId } = await params;

    if (!threadId) {
      return NextResponse.json(
        { error: 'Thread ID is required' },
        { status: 400 }
      );
    }

    const fastApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    const response = await fetch(
      `${fastApiUrl}/api/conversations/${encodeURIComponent(threadId)}/restore`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // @ts-ignore - agent option exists but not in types
        agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to restore conversation' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error restoring conversation:', error);
    return NextResponse.json(
      { error: 'Failed to restore conversation', details: error.message },
      { status: 500 }
    );
  }
}
