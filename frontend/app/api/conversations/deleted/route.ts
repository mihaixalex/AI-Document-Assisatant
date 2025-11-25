// app/api/conversations/deleted/route.ts
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

export async function GET(request: NextRequest) {
  try {
    const fastApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '50';
    const offset = searchParams.get('offset') || '0';

    const response = await fetch(
      `${fastApiUrl}/api/conversations/deleted?limit=${limit}&offset=${offset}`,
      {
        method: 'GET',
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
        { error: errorData.detail || 'Failed to fetch deleted conversations' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error fetching deleted conversations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch deleted conversations', details: error.message },
      { status: 500 }
    );
  }
}
