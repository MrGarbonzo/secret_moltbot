import { NextRequest, NextResponse } from 'next/server';

const AGENT_URL = process.env.AGENT_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${AGENT_URL}/api/${path}${searchParams ? `?${searchParams}` : ''}`;

  const response = await fetch(url);
  const data = await response.json();

  return NextResponse.json(data, { status: response.status });
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const body = await request.text();
  const url = `${AGENT_URL}/api/${path}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body || undefined,
  });
  const data = await response.json();

  return NextResponse.json(data, { status: response.status });
}
