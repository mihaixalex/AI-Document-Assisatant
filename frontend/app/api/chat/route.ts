import { NextResponse } from 'next/server';
import { retrievalAssistantStreamConfig } from '@/constants/graphConfigs';
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

export async function POST(req: Request) {
  try {
    const { message, threadId } = await req.json();

    if (!message) {
      return new NextResponse(
        JSON.stringify({ error: 'Message is required' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    }

    if (!threadId || threadId.trim() === '') {
      return new NextResponse(
        JSON.stringify({ error: 'Thread ID cannot be empty or whitespace' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    }

    const fastApiUrl =
      process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    try {
      // Call FastAPI backend with IPv4-only agent
      const response = await fetch(`${fastApiUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          threadId,
          config: {
            configurable: {
              ...retrievalAssistantStreamConfig,
              thread_id: threadId,
            },
          },
        }),
        // @ts-ignore - agent option exists but not in types
        agent: fastApiUrl.startsWith('https') ? httpsAgent : httpAgent,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'FastAPI request failed');
      }

      // Return the streaming response from FastAPI
      return new Response(response.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
      });
    } catch (error) {
      // Handle FastAPI communication errors
      console.error('FastAPI communication error:', error);
      return new NextResponse(
        JSON.stringify({
          error: 'Failed to communicate with backend',
          details: error instanceof Error ? error.message : 'Unknown error',
        }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    }
  } catch (error) {
    // Handle JSON parsing errors
    console.error('Route error:', error);
    return new NextResponse(
      JSON.stringify({ error: 'Internal server error' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  }
}
