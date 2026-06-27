---
title: "gRPC: when REST isn't the right protocol."
description: "gRPC trades REST's universality for performance, strict contracts, and bidirectional streaming. Here's what that trade buys you and when it's worth making."
pubDate: 2026-05-04
tags: ["gRPC", "Architecture"]
draft: false
---

REST has won the API design debate for most web applications. It's simple, HTTP-native, and supported by every tool in existence. But REST makes assumptions — stateless requests, text-based JSON payloads, resource-oriented URLs — that aren't always the right fit. gRPC starts from different assumptions and excels in the contexts where REST struggles.

## What gRPC actually is

gRPC is an RPC (Remote Procedure Call) framework from Google, built on HTTP/2 and Protocol Buffers. Instead of designing around resources and HTTP verbs, you define a service with typed methods. The framework generates client and server code from that definition.

```protobuf
// user.proto
syntax = "proto3";

service UserService {
  rpc GetUser (GetUserRequest) returns (User);
  rpc ListUsers (ListUsersRequest) returns (stream User);
  rpc CreateUser (CreateUserRequest) returns (User);
  rpc WatchUserEvents (WatchRequest) returns (stream UserEvent);
}

message GetUserRequest {
  string user_id = 1;
}

message User {
  string id = 1;
  string email = 2;
  string name = 3;
  int64 created_at = 4;
}

message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;
}
```

Running `protoc` on this file generates typed client and server stubs in any supported language. The client code looks like calling a local function; the network call is abstracted away.

## Where gRPC outperforms REST

**Payload size.** Protocol Buffers serialize to binary, typically 3-10x smaller than equivalent JSON. For high-throughput services exchanging thousands of messages per second, this matters.

**Performance on HTTP/2.** gRPC runs over HTTP/2, which multiplexes multiple streams over a single connection, uses header compression, and enables bidirectional streaming natively.

**Streaming.** REST can stream responses (via Server-Sent Events or chunked transfer), but gRPC treats streaming as a first-class primitive with four patterns:

```protobuf
service DataService {
  // Unary: one request, one response
  rpc GetItem (GetItemRequest) returns (Item);

  // Server streaming: one request, stream of responses
  rpc ListItems (ListRequest) returns (stream Item);

  // Client streaming: stream of requests, one response
  rpc UploadItems (stream Item) returns (UploadResult);

  // Bidirectional streaming: stream in both directions
  rpc SyncItems (stream SyncRequest) returns (stream SyncResponse);
}
```

Bidirectional streaming is particularly powerful for real-time data feeds, collaborative editing, or any scenario where the server and client need to exchange events continuously.

**Strict contracts.** The `.proto` file is a schema that both client and server must conform to. If the server changes the shape of a response, the client won't compile until it's updated. This is more rigid than REST but eliminates a category of runtime errors.

## A Node.js server example

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';

const packageDef = protoLoader.loadSync('user.proto');
const proto = grpc.loadPackageDefinition(packageDef) as any;

const server = new grpc.Server();

server.addService(proto.UserService.service, {
  getUser: async (call: grpc.ServerUnaryCall<any, any>, callback: grpc.sendUnaryData<any>) => {
    const user = await db.users.findById(call.request.user_id);
    if (!user) {
      return callback({ code: grpc.status.NOT_FOUND, message: 'User not found' });
    }
    callback(null, { id: user.id, email: user.email, name: user.name });
  },

  listUsers: async (call: grpc.ServerWritableStream<any, any>) => {
    const users = await db.users.findAll({ pageSize: call.request.page_size });
    for (const user of users) {
      call.write({ id: user.id, email: user.email, name: user.name });
    }
    call.end();
  },
});

server.bindAsync('0.0.0.0:50051', grpc.ServerCredentials.createInsecure(), () => {
  server.start();
});
```

## What gRPC gives up

Browser support is incomplete. gRPC-Web requires a proxy layer (like Envoy) between the browser and the gRPC server, because browsers don't have direct access to HTTP/2 trailers that gRPC requires. Most gRPC deployments are service-to-service, not browser-to-server.

Observability tools designed for HTTP/1.1 and JSON don't work out of the box with gRPC's binary format. You need gRPC-aware tooling for logging, tracing, and debugging.

The `.proto` contract that enforces type safety also creates coupling. Changing an API requires coordinating schema updates across all consumers.

## When to reach for gRPC

gRPC earns its complexity in internal service-to-service communication where performance and strong contracts matter: microservice backends, data pipelines, ML inference APIs, or any system where services communicate at high volume over a controlled network. For public APIs consumed by arbitrary clients, REST or GraphQL remain better choices.
