use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use dashmap::DashMap;
use futures::SinkExt;
use tokio::sync::Mutex;
use uuid::Uuid;

use crate::error::WsError;
use crate::messages::WsMessage;

/// A single WebSocket connection (one browser tab).
pub struct WsConnection {
    pub id: Uuid,
    pub user_id: Uuid,
    pub organization_id: Option<Uuid>,
    pub sender: Mutex<futures::stream::SplitSink<
        axum::extract::ws::WebSocket,
        axum::extract::ws::Message,
    >>,
}

/// Thread-safe manager for all active WebSocket connections.
///
/// Uses DashMap for concurrent access without global locks.
/// Each user can have multiple connections (multiple tabs).
pub struct ConnectionManager {
    /// user_id -> list of connections for that user
    connections: DashMap<Uuid, Vec<Arc<WsConnection>>>,
    /// org_id -> list of user_ids in that org (for broadcast)
    org_members: DashMap<Uuid, Vec<Uuid>>,
    /// Total connection count
    count: AtomicUsize,
}

impl ConnectionManager {
    pub fn new() -> Self {
        Self {
            connections: DashMap::new(),
            org_members: DashMap::new(),
            count: AtomicUsize::new(0),
        }
    }

    /// Register a new WebSocket connection for a user.
    /// Returns the connection ID for later unsubscribe.
    pub fn subscribe(
        &self,
        user_id: Uuid,
        organization_id: Option<Uuid>,
        sender: futures::stream::SplitSink<
            axum::extract::ws::WebSocket,
            axum::extract::ws::Message,
        >,
    ) -> Uuid {
        let conn_id = Uuid::new_v4();
        let conn = Arc::new(WsConnection {
            id: conn_id,
            user_id,
            organization_id,
            sender: Mutex::new(sender),
        });

        self.connections
            .entry(user_id)
            .or_default()
            .push(conn);

        if let Some(org_id) = organization_id {
            let mut members = self.org_members.entry(org_id).or_default();
            if !members.contains(&user_id) {
                members.push(user_id);
            }
        }

        self.count.fetch_add(1, Ordering::Relaxed);
        tracing::info!(
            user_id = %user_id,
            conn_id = %conn_id,
            "WebSocket connection registered"
        );
        conn_id
    }

    /// Remove a connection by its ID.
    pub fn unsubscribe(&self, connection_id: Uuid) {
        let mut removed = false;

        // Iterate all users and remove the matching connection
        self.connections.retain(|_user_id, conns| {
            let before = conns.len();
            conns.retain(|c| c.id != connection_id);
            if conns.len() < before {
                removed = true;
            }
            // Keep the entry only if there are connections remaining
            !conns.is_empty()
        });

        if removed {
            self.count.fetch_sub(1, Ordering::Relaxed);
            tracing::info!(conn_id = %connection_id, "WebSocket connection removed");
        }
    }

    /// Send a message to all connections of a specific user.
    pub async fn send_to_user(&self, user_id: Uuid, message: &WsMessage) -> Result<(), WsError> {
        let json = serde_json::to_string(message)
            .map_err(|e| WsError::Message(format!("serialization failed: {e}")))?;

        let conns = self.connections.get(&user_id);
        if let Some(conns) = conns {
            for conn in conns.iter() {
                let mut sender = conn.sender.lock().await;
                if let Err(e) = sender
                    .send(axum::extract::ws::Message::Text(json.clone().into()))
                    .await
                {
                    tracing::warn!(
                        conn_id = %conn.id,
                        user_id = %user_id,
                        "Failed to send message: {e}"
                    );
                }
            }
        }
        Ok(())
    }

    /// Broadcast a message to all users in an organization.
    pub async fn send_to_org(&self, org_id: Uuid, message: &WsMessage) -> Result<(), WsError> {
        let user_ids: Vec<Uuid> = self
            .org_members
            .get(&org_id)
            .map(|members| members.clone())
            .unwrap_or_default();

        for user_id in user_ids {
            self.send_to_user(user_id, message).await?;
        }
        Ok(())
    }

    /// Get the total number of active connections.
    pub fn connection_count(&self) -> usize {
        self.count.load(Ordering::Relaxed)
    }

    /// Get the number of unique users with active connections.
    pub fn users_online(&self) -> usize {
        self.connections.len()
    }

    /// Remove all connections for a given user (e.g., on disconnect cleanup).
    pub fn remove_user(&self, user_id: Uuid) {
        if let Some((_, conns)) = self.connections.remove(&user_id) {
            let removed_count = conns.len();
            self.count.fetch_sub(removed_count, Ordering::Relaxed);
            tracing::info!(
                user_id = %user_id,
                removed = removed_count,
                "All connections removed for user"
            );
        }
    }
}

impl Default for ConnectionManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Connection manager unit tests that don't require actual WebSocket connections
    #[test]
    fn test_new_manager_empty() {
        let mgr = ConnectionManager::new();
        assert_eq!(mgr.connection_count(), 0);
        assert_eq!(mgr.users_online(), 0);
    }

    #[test]
    fn test_default_trait() {
        let mgr = ConnectionManager::default();
        assert_eq!(mgr.connection_count(), 0);
    }
}
