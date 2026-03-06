use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Outgoing messages sent from server to client.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsMessage {
    CoachMessage {
        session_id: Uuid,
        content: String,
        phase: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        hint: Option<String>,
    },
    Notification {
        id: Uuid,
        #[serde(rename = "notification_type")]
        notification_type: String,
        title: String,
        body: String,
    },
    TypingIndicator {
        session_id: Uuid,
        is_typing: bool,
    },
    Ping,
    Pong,
}

/// Incoming messages received from client.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum IncomingMessage {
    ChatMessage {
        session_id: Uuid,
        content: String,
    },
    Subscribe {
        channels: Vec<String>,
    },
    Ping,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ws_message_serialize_coach() {
        let msg = WsMessage::CoachMessage {
            session_id: Uuid::nil(),
            content: "Hello".into(),
            phase: "intro".into(),
            hint: Some("Try again".into()),
        };
        let json = serde_json::to_string(&msg).expect("serialize");
        assert!(json.contains("\"type\":\"coach_message\""));
        assert!(json.contains("\"hint\":\"Try again\""));
    }

    #[test]
    fn test_ws_message_serialize_notification() {
        let msg = WsMessage::Notification {
            id: Uuid::nil(),
            notification_type: "mission_complete".into(),
            title: "Done".into(),
            body: "You did it".into(),
        };
        let json = serde_json::to_string(&msg).expect("serialize");
        assert!(json.contains("\"type\":\"notification\""));
        assert!(json.contains("\"notification_type\":\"mission_complete\""));
    }

    #[test]
    fn test_ws_message_no_hint_omitted() {
        let msg = WsMessage::CoachMessage {
            session_id: Uuid::nil(),
            content: "Hello".into(),
            phase: "intro".into(),
            hint: None,
        };
        let json = serde_json::to_string(&msg).expect("serialize");
        assert!(!json.contains("hint"));
    }

    #[test]
    fn test_incoming_message_deserialize_chat() {
        let json = r#"{"type":"chat_message","session_id":"00000000-0000-0000-0000-000000000000","content":"hi"}"#;
        let msg: IncomingMessage = serde_json::from_str(json).expect("deserialize");
        assert_eq!(
            msg,
            IncomingMessage::ChatMessage {
                session_id: Uuid::nil(),
                content: "hi".into(),
            }
        );
    }

    #[test]
    fn test_incoming_message_deserialize_subscribe() {
        let json = r#"{"type":"subscribe","channels":["org:abc","user:xyz"]}"#;
        let msg: IncomingMessage = serde_json::from_str(json).expect("deserialize");
        assert_eq!(
            msg,
            IncomingMessage::Subscribe {
                channels: vec!["org:abc".into(), "user:xyz".into()],
            }
        );
    }

    #[test]
    fn test_incoming_message_deserialize_ping() {
        let json = r#"{"type":"ping"}"#;
        let msg: IncomingMessage = serde_json::from_str(json).expect("deserialize");
        assert_eq!(msg, IncomingMessage::Ping);
    }

    #[test]
    fn test_ws_message_ping_pong() {
        let ping_json = serde_json::to_string(&WsMessage::Ping).expect("serialize");
        assert!(ping_json.contains("\"type\":\"ping\""));

        let pong_json = serde_json::to_string(&WsMessage::Pong).expect("serialize");
        assert!(pong_json.contains("\"type\":\"pong\""));
    }
}
