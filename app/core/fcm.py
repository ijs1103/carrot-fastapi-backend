import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging

logger = logging.getLogger(__name__)

# 서비스 계정 키 경로
# 실제 배포 환경에서는 환경 변수 등으로 관리하는 것이 좋습니다.
CRED_PATH = os.path.join(os.path.dirname(__file__), "credentials", "serviceAccountKey.json")

firebase_app = None

def init_firebase():
    global firebase_app
    if firebase_app:
        return
        
    if not os.path.exists(CRED_PATH):
        logger.warning(f"Firebase service account key not found at {CRED_PATH}. Notifications will not be sent.")
        return

    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

# 초기화 시도
init_firebase()

async def send_chat_notification(token: str, room_id: str, sender_name: str, message: str):
    """
    FCM을 통해 채팅 알림을 보냅니다.
    """
    if not firebase_app:
        # 초기화가 안 되어 있으면 시도 (파일이 나중에 추가되었을 수 있으므로)
        init_firebase()
        if not firebase_app:
            print("[FCM] Skip sending: Firebase app not initialized.")
            return

    if not token:
        print("[FCM] Skip sending: No target token provided.")
        return

    try:
        fcm_message = messaging.Message(
            notification=messaging.Notification(
                title=f"{sender_name}",
                body=message,
            ),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='chat_notifications',
                    priority='high',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1,
                        content_available=True,
                    ),
                ),
            ),
            data={
                "roomId": str(room_id),
                "type": "chat"
            },
            token=token,
        )

        response = messaging.send(fcm_message)
        print(f"[FCM] [SUCCESS] sent message to {token[:10]}...: {response}")
        return response

    except Exception as e:
        print(f"[FCM] [ERROR] failed to send message: {e}")
        return None
