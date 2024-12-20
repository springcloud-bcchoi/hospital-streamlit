import streamlit as st
import socket
import json

# 소켓 연결을 유지하는 글로벌 변수
client_socket = None

def initialize_socket(server_ip, server_port):
    global client_socket
    if client_socket is None:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_ip, server_port))
        except Exception as e:
            st.error(f"Failed to connect to server: {e}")

def send_control_message(uid, command, value):
    """
    Control 메시지를 서버로 전송하는 함수
    """
    global client_socket
    try:
        if client_socket is None:
            return {"status": "error", "error": "Socket is not initialized."}

        # Control 메시지 생성
        message = {
            "type": "control",
            "uid": uid,
            "command": command,
            "value": value
        }

        # JSON 직렬화 후 전송
        client_socket.sendall(json.dumps(message).encode('utf-8'))

        # 서버 응답 수신
        response = client_socket.recv(8192)
        return json.loads(response.decode('utf-8'))

    except Exception as e:
        return {"status": "error", "error": str(e)}

# Streamlit UI
st.title("Control Command Interface")

# 서버 정보 입력
st.sidebar.header("Server Configuration")
server_ip = st.sidebar.text_input("Server IP", "127.0.0.1")
server_port = st.sidebar.number_input("Server Port", value=8080, step=1)

if st.sidebar.button("Connect to Server"):
    initialize_socket(server_ip, int(server_port))

# Control 메시지 입력
st.header("Send Control Message")
uid = st.text_input("UID", "device123")
command = st.text_input("Command", "start")
value = st.text_input("Value (optional)", "")

# 전송 버튼
if st.button("Send Command"):
    if not uid or not command:
        st.error("UID와 Command는 필수 항목입니다.")
    else:
        # 서버로 Control 메시지 전송
        response = send_control_message(uid, command, value)

        # 응답 결과 표시
        if response.get("status") == "success":
            st.success("Command sent successfully!")
            st.json(response)
        else:
            st.error("Failed to send command.")
            st.json(response)
