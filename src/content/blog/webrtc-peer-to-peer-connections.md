---
title: "WebRTC: peer-to-peer connections from the browser."
description: "WebRTC enables direct browser-to-browser communication for video, audio, and data — without routing media through a server. Here's how the connection setup actually works."
pubDate: 2026-04-30
tags: ["WebRTC", "JavaScript"]
draft: false
---

WebRTC lets two browsers communicate directly with each other. Video, audio, and arbitrary data can flow peer-to-peer without passing through your application server. The result is lower latency and less server bandwidth — but the connection setup process is more involved than a typical HTTP request.

## The signaling problem

Peers can't connect directly without first exchanging connection information. This exchange — called signaling — has to happen through a server, because the peers don't know each other's addresses yet. WebRTC doesn't define how signaling works; you implement it yourself using WebSockets, HTTP, or any transport you choose.

What gets exchanged during signaling:

- **SDP offers and answers**: session description protocol documents that describe the peer's media capabilities (codecs, resolutions) and connection parameters.
- **ICE candidates**: potential network paths the peer can be reached through, collected by the browser from local network interfaces and STUN servers.

## Establishing a connection

Here's a minimal example of the peer-to-peer setup:

```javascript
// Both peers run this setup code
async function createPeerConnection(onSignal) {
  const pc = new RTCPeerConnection({
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' }, // public STUN server
    ],
  });

  // As ICE candidates are discovered, send them to the remote peer
  pc.onicecandidate = (event) => {
    if (event.candidate) {
      onSignal({ type: 'ice-candidate', candidate: event.candidate });
    }
  };

  return pc;
}

// Caller side
async function startCall(signalingChannel) {
  const pc = await createPeerConnection((signal) => {
    signalingChannel.send(signal);
  });

  // Add local media stream
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  stream.getTracks().forEach(track => pc.addTrack(track, stream));

  // Create and send an offer
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  signalingChannel.send({ type: 'offer', sdp: offer });

  // Handle incoming signals
  signalingChannel.on('message', async (signal) => {
    if (signal.type === 'answer') {
      await pc.setRemoteDescription(signal.sdp);
    } else if (signal.type === 'ice-candidate') {
      await pc.addIceCandidate(signal.candidate);
    }
  });

  return pc;
}

// Callee side
async function answerCall(signalingChannel, offer) {
  const pc = await createPeerConnection((signal) => {
    signalingChannel.send(signal);
  });

  // Display incoming video
  pc.ontrack = (event) => {
    const remoteVideo = document.getElementById('remote-video');
    remoteVideo.srcObject = event.streams[0];
  };

  await pc.setRemoteDescription(offer.sdp);

  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  stream.getTracks().forEach(track => pc.addTrack(track, stream));

  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  signalingChannel.send({ type: 'answer', sdp: answer });

  signalingChannel.on('message', async (signal) => {
    if (signal.type === 'ice-candidate') {
      await pc.addIceCandidate(signal.candidate);
    }
  });
}
```

## Data channels

WebRTC isn't only for media. Data channels let you send arbitrary binary or text data between peers:

```javascript
// Sender creates a data channel
const dataChannel = pc.createDataChannel('chat', {
  ordered: true,       // TCP-like ordering
  // maxRetransmits: 0  // UDP-like, unreliable — useful for game state
});

dataChannel.onopen = () => {
  dataChannel.send(JSON.stringify({ type: 'message', text: 'Hello!' }));
};

// Receiver listens for the channel
pc.ondatachannel = (event) => {
  const channel = event.channel;
  channel.onmessage = (e) => {
    const message = JSON.parse(e.data);
    console.log('Received:', message.text);
  };
};
```

Data channels support both reliable (ordered) and unreliable (unordered) modes. Unreliable mode is useful for applications like games where stale state updates are worse than missing ones.

## STUN and TURN servers

STUN servers help peers discover their public IP address and port — necessary when they're behind NAT. Most peer connections succeed with just STUN.

TURN servers relay media when a direct connection isn't possible (some corporate firewalls block peer-to-peer UDP). TURN adds server bandwidth costs but is necessary for reliable connectivity in restrictive network environments.

```javascript
const pc = new RTCPeerConnection({
  iceServers: [
    { urls: 'stun:stun.example.com:3478' },
    {
      urls: 'turn:turn.example.com:3478',
      username: 'user',
      credential: 'secret',
    },
  ],
});
```

## When WebRTC is the right choice

WebRTC fits use cases where media or real-time data needs to travel between clients with minimal latency: video calls, screen sharing, collaborative editors, multiplayer games. The server only handles signaling — it doesn't touch the media stream at all.

For large group calls (more than 3-4 participants), a Selective Forwarding Unit (SFU) media server becomes necessary to avoid each peer having to send separate streams to every other participant. But the signaling and connection model remains the same.
