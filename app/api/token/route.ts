import {
  AccessToken,
  RoomAgentDispatch,
  RoomConfiguration,
  TrackSource,
} from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";

import { readDemoSessionFromRequest } from "@/web/lib/server-session";

export async function POST(request: NextRequest) {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const serverUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !serverUrl) {
    return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
  }

  try {
    const session = await readDemoSessionFromRequest(request);
    if (!session) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const roomName = `hr-demo-${crypto.randomUUID()}`;
    const agentName = process.env.VOICE_AGENT_NAME || "hr-assistant";

    const token = new AccessToken(apiKey, apiSecret, {
      identity: session.userId,
      name: session.name,
      attributes: {
        app: "hrms-demo",
        "hrms.user_id": session.userId,
        "hrms.role": session.role,
      },
      ttl: "10m",
    });
    token.addGrant({
      roomJoin: true,
      room: roomName,
      canPublishSources: [TrackSource.MICROPHONE],
      canPublishData: false,
      canSubscribe: true,
    });
    token.roomConfig = new RoomConfiguration({
      agents: [new RoomAgentDispatch({ agentName })],
    });

    return NextResponse.json(
      { server_url: serverUrl, participant_token: await token.toJwt() },
      { status: 201 },
    );
  } catch {
    return NextResponse.json({ error: "Failed to generate token" }, { status: 500 });
  }
}
