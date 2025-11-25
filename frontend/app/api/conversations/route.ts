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

// GET /api/conversations - List all conversations
export async function GET() {
  try {
    const fastApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    const response = await fetch(`${fastApiUrl}/api/conversations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // @ts-ignore - agent option exists but not in types
      agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to fetch conversations');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching conversations:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch conversations',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// POST /api/conversations - Create a new conversation
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { title } = body;

    if (!title) {
      return NextResponse.json(
        { error: 'Title is required' },
        { status: 400 }
      );
    }

    const fastApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    const response = await fetch(`${fastApiUrl}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
      // @ts-ignore - agent option exists but not in types
      agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to create conversation');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error creating conversation:', error);
    return NextResponse.json(
      {
        error: 'Failed to create conversation',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
