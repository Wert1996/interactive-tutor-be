# WebSocket Contract - Learning Interface

## Endpoint
`/learning-interface`

## Overview
The Learning Interface WebSocket provides real-time communication between the frontend client and the backend learning system. It handles session management, student interactions, and delivers various learning commands including speech, visual content, and assessments.

## Message Format
All messages are JSON objects sent and received as text through the WebSocket connection.

---

## Client to Server Messages

### 1. Ping Message
**Purpose**: Check server connectivity
```json
{
  "type": "ping"
}
```

### 2. Start Session
**Purpose**: Initialize a learning session
```json
{
  "type": "start_session",
  "session_id": "string"
}
```

### 3. Next Phase
**Purpose**: Advance to the next phase of the current module
```json
{
  "type": "next_phase",
  "session_id": "string"
}
```

### 4. Student Interactions
**Purpose**: Handle student input and responses

#### 4.1 Speech Interaction
```json
{
  "type": "speech",
  "session_id": "string",
  "audio_bytes": "base64_encoded_audio_data"
}
```

#### 4.2 Multiple Choice Question Response
```json
{
  "type": "mcq_question",
  "session_id": "string",
  "mcq_question": {
    "answer": "string"
  }
}
```

---

## Server to Client Messages

### 1. Pong Response
**Purpose**: Response to ping message
```json
{
  "type": "pong",
  "message": "Server is alive",
  "timestamp": "ISO8601_timestamp"
}
```

### 2. Error Response
**Purpose**: Communicate errors to the client
```json
{
  "type": "error",
  "message": "Error description",
  "timestamp": "ISO8601_timestamp"
}
```

### 3. Module Completion
**Purpose**: Indicate that a module has been completed
```json
{
  "type": "finish_module",
  "message": "Module finished"
}
```

### 4. Learning Commands
**Purpose**: Deliver learning content and interactions

The server sends an array of command objects. Each command has the following structure:
```json
{
  "type": "COMMAND_TYPE",
  "payload": { /* command-specific payload */ }
}
```

#### 4.1 Teacher Speech Command
```json
{
  "type": "TEACHER_SPEECH",
  "payload": {
    "text": "string",
    "audio_bytes": "base64_encoded_audio_data"
  }
}
```

#### 4.2 Classmate Speech Command
```json
{
  "type": "CLASSMATE_SPEECH",
  "payload": {
    "text": "string",
    "audio_bytes": "base64_encoded_audio_data"
  }
}
```

#### 4.3 Whiteboard Command
```json
{
  "type": "WHITEBOARD",
  "payload": {
    "html": "string"
  }
}
```

#### 4.4 Multiple Choice Question Command
```json
{
  "type": "MCQ_QUESTION",
  "payload": {
    "question": "string",
    "options": [
      {
        "text": "option_text",
        "correct": boolean
      }
    ]
  }
}
```

#### 4.5 Finish Module Command
```json
{
  "type": "FINISH_MODULE",
  "payload": {}
}
```

---

## Command Types Reference

| Command Type | Description |
|--------------|-------------|
| `TEACHER_SPEECH` | Audio and text content delivered by the teacher |
| `CLASSMATE_SPEECH` | Audio and text content delivered by a classmate character |
| `WHITEBOARD` | HTML content to be displayed on a whiteboard interface |
| `MCQ_QUESTION` | Multiple choice questions for student assessment |
| `FINISH_MODULE` | Indicates the current module is complete |

---

## Error Handling

### Common Error Scenarios

1. **Session Not Found**
```json
{
  "type": "error",
  "message": "Session with id {session_id} not found",
  "timestamp": "ISO8601_timestamp"
}
```

2. **Course Not Found**
```json
{
  "type": "error",
  "message": "Course with id {course_id} not found",
  "timestamp": "ISO8601_timestamp"
}
```

3. **Invalid JSON**
```json
{
  "type": "error",
  "message": "Invalid JSON format"
}
```

4. **Unknown Message Type**
```json
{
  "type": "error",
  "message": "Unknown message type: {message_type}",
  "timestamp": "ISO8601_timestamp"
}
```

---

## Usage Flow

1. **Connect** to the WebSocket endpoint
2. **Send** a `start_session` message with a valid session ID
3. **Receive** learning commands and display them to the user
4. **Send** student interactions (speech or MCQ responses) as they occur
5. **Send** `next_phase` messages to advance through the learning content
6. **Handle** error messages appropriately
7. **Disconnect** when the session is complete

---

## Notes

- All audio data is base64 encoded
- Timestamps are in ISO8601 format
- The server may send multiple commands in a single response array
- Commands should be processed in the order they appear in the array
- Audio bytes are generated for speech commands and should be played back to the user
- HTML content in whiteboard commands should be sanitized before display 