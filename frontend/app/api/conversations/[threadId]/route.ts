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

// PATCH /api/conversations/[threadId] - Update a conversation title
export async function PATCH(
  request: NextRequest,
  { params }: { params: { threadId: string } }
) {
  try {
    const { threadId } = params;

    if (!threadId || threadId.trim() === '') {
      return NextResponse.json(
        { error: 'Thread ID cannot be empty or whitespace' },
        { status: 400 }
      );
    }

    const body = await request.json();

    if (!body.title || typeof body.title !== 'string' || body.title.trim() === '') {
      return NextResponse.json(
        { error: 'Title is required and cannot be empty' },
        { status: 400 }
      );
    }

    const fastApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    const response = await fetch(`${fastApiUrl}/api/conversations/${encodeURIComponent(threadId)}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title: body.title.trim() }),
      // @ts-ignore - agent option exists but not in types
      agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to update conversation');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating conversation:', error);
    return NextResponse.json(
      {
        error: 'Failed to update conversation',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// DELETE /api/conversations/[threadId] - Delete a conversation
export async function DELETE(
  request: NextRequest,
  { params }: { params: { threadId: string } }
) {
  try {
    const { threadId } = params;

    if (!threadId || threadId.trim() === '') {
      return NextResponse.json(
        { error: 'Thread ID cannot be empty or whitespace' },
        { status: 400 }
      );
    }

    const fastApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    const response = await fetch(`${fastApiUrl}/api/conversations/${encodeURIComponent(threadId)}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      // @ts-ignore - agent option exists but not in types
      agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to delete conversation');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error deleting conversation:', error);
    return NextResponse.json(
      {
        error: 'Failed to delete conversation',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
