import streamlit as st
import socket
import json

# 소켓 초기화 함수
def initialize_socket(server_ip, server_port):
    try:
        # 소켓 객체 생성 및 연결
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, server_port))
        return sock
    except Exception as e:
        st.error(f"Failed to connect to server: {e}")
        return None

# Control 메시지 전송 함수
def send_control_message(client_socket, uid, command, value):
    """
    Control 메시지를 서버로 전송하는 함수
    """
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
server_ip = st.sidebar.text_input("Server IP", "kibana.a2uictai.com")
server_port = st.sidebar.number_input("Server Port", value=0000, step=1)

# 서버 연결
if "client_socket" not in st.session_state:
    st.session_state.client_socket = None

if st.sidebar.button("Connect to Server"):
    st.session_state.client_socket = initialize_socket(server_ip, int(server_port))

# 소켓 상태 표시
st.sidebar.subheader("Socket Status")
if st.session_state.client_socket:
    st.sidebar.success("Socket is connected.")
else:
    st.sidebar.warning("Socket is not connected.")

# Control 메시지 입력
st.header("Send Control Message")
uid = st.text_input("UID", "device123")
command = st.text_input("Command", "reset")
value = st.text_input("Value (optional)", "")

# 전송 버튼 상태 관리
if "is_sending" not in st.session_state:
    st.session_state.is_sending = False

if st.button("Send Command", disabled=st.session_state.is_sending):
    if not uid.strip() or not command.strip():
        st.error("UID와 Command는 필수 항목입니다.")
    else:
        # 입력값 가져오기
        uid_value = uid.strip()
        command_value = command.strip()
        optional_value = value.strip()

        st.session_state.is_sending = True
        with st.spinner("Sending command..."):
            response = send_control_message(st.session_state.client_socket, uid_value, command_value, optional_value)

        # 응답 결과 표시
        if response.get("status") == "success":
            st.success("Command sent successfully!")
            st.json(response)
        else:
            st.error("Failed to send command.")
            st.json(response)

        st.session_state.is_sending = False
