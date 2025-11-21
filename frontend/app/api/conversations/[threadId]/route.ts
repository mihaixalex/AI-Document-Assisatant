/**
 * API proxy routes for individual conversation operations.
 * Handles GET (history), PATCH (update), and DELETE operations.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

interface RouteParams {
  params: {
    threadId: string;
  };
}

/**
 * GET /api/conversations/[threadId] - Get conversation history
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { threadId } = params;

    const response = await fetch(
      `${API_BASE_URL}/api/conversations/${threadId}/history`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${error}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error getting conversation history:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Failed to get conversation history',
      },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/conversations/[threadId] - Update conversation title
 */
export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const { threadId } = params;
    const body = await request.json();

    const response = await fetch(
      `${API_BASE_URL}/api/conversations/${threadId}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${error}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating conversation:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Failed to update conversation',
      },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/conversations/[threadId] - Delete conversation
 */
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { threadId } = params;

    const response = await fetch(
      `${API_BASE_URL}/api/conversations/${threadId}`,
      {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${error}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error deleting conversation:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Failed to delete conversation',
      },
      { status: 500 }
    );
  }
}
