import {
  AccessToken,
  RoomAgentDispatch,
  RoomConfiguration,
  TrackSource,
} from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";

export async function POST(_request?: NextRequest) {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const serverUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !serverUrl) {
    return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
  }

  try {
    const roomName = `hr-demo-${crypto.randomUUID()}`;
    const agentName = process.env.VOICE_AGENT_NAME || "hr-assistant";

    const token = new AccessToken(apiKey, apiSecret, {
      identity: "EMP-1042",
      name: "Maya Patel",
      attributes: { app: "hrms-demo" },
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
