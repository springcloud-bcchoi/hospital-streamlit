import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import socket
import threading
import logging

# 타이틀 설정
st.title("Hospital Radar Data with Command Sender")

# 사용자 입력 UI
# Prometheus 쿼리 선택
query = st.selectbox(
    "Select Prometheus Query:",
    [
        "radar_v2_breath",
        "radar_v2_heart",
        "radar_v2_detect_count",
        "radar_v2_fall",
        "radar_v2_presence",
        "radar_v2_range",
        "radar_v2_rssi",
    ]
)
selected_date = st.date_input("Select a Date")
start_time = st.selectbox("Select Start Time (End Time will be 3 hours later)",
                          [f"{str(i).zfill(2)}:00:00" for i in range(0, 24, 3)])
step = st.number_input("Step (in seconds, minimum 6):", min_value=6, value=10, step=1)

# API URL
PROMETHEUS_API_URL = "https://3iztvmb7bj.execute-api.ap-northeast-2.amazonaws.com/prometheus/v1/query_range"


# 서버 정보
SERVER_IP = "kibana.a2uictai.com"
SERVER_PORT = 17095

# 명령어 목록과 기본값
COMMANDS = {
    "help": "help",
    "info": "info",
    "freset": "freset",
    "reset": "reset",
    "save": "save",
    "stop": "stop",
    "start": "start",
    "mins": "mins <value>",
    "minp": "minp <value>",
    "maxp": "maxp <value>",
    "hangdis": "hangdis <value>",
    "hangthr": "hangthr <value>",
    "meast": "meast <value>",
    "xleft": "xleft <value>",
    "xright": "xright <value>",
    "yleft": "yleft <value>",
    "yright": "yright <value>",
}


# 상태 관리 변수
response_data = None  # 서버 응답 저장
is_waiting_for_response = False  # 응답 대기 상태

# 서버 응답 수신 함수 (비동기적으로 실행)
def receive_response(sock):
    global response_data, is_waiting_for_response
    try:
        while is_waiting_for_response:
            response = sock.recv(4096).decode("utf-8")
            if response:
                response_data = json.loads(response)
                is_waiting_for_response = False  # 응답 완료
                break
    except Exception as e:
        response_data = {"status": "error", "error": str(e)}
        is_waiting_for_response = False


# 데이터 캐시
@st.cache_data
def fetch_data(date, start_time, step, query):
    start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
    end_datetime = start_datetime + timedelta(hours=3)
    params = {
        "query": query,
        "start": start_datetime.isoformat() + "Z",
        "end": end_datetime.isoformat() + "Z",
        "step": str(step)
    }
    response = requests.get(PROMETHEUS_API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    job_data = {}
    if data.get('status') == 'success':
        results = data['data']['result']
        for result in results:
            job = result['metric']['job']
            if "21b7" in job:
                plot_data = []
                for timestamp, value in result['values']:
                    plot_data.append({
                        'timestamp': datetime.utcfromtimestamp(timestamp),
                        'value': float(value)
                    })
                df = pd.DataFrame(plot_data)
                job_data[job] = df
    return job_data

# Fetch Data
try:
    all_data = fetch_data(selected_date, start_time, step, query)
    st.success("Data fetched successfully!")
except Exception as e:
    st.error(f"Error fetching data: {e}")
    all_data = {}

# Job 선택 UI
if all_data:
    jobs = list(all_data.keys())
    selected_job = st.selectbox("Select a Job", jobs)

    # 선택된 Job 데이터 표시
    if selected_job:
        df = all_data[selected_job]
        start_datetime = datetime.strptime(f"{selected_date} {start_time}", "%Y-%m-%d %H:%M:%S")
        end_datetime = start_datetime + timedelta(hours=3)

        # 테이블 표시
        st.subheader(f"Data Table for Job: {selected_job}")
        st.write(df)

        # 그래프 표시
        st.subheader(f"Time Series Graph for Job: {selected_job}")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df['timestamp'], df['value'], label=selected_job, marker='o')
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Value")
        ax.set_title(f"Time Series Data for Job: {selected_job}")
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # CSV 다운로드 버튼
        csv = df.to_csv(index=False)
        # 파일 이름 간소화
        start_str = start_datetime.strftime("%H")
        end_str = end_datetime.strftime("%H")
        file_name = f"{selected_date}_{start_str}T{end_str}_{selected_job}_{query}.csv"
        st.download_button(
            label=f"Download Data for {selected_job}",
            data=csv,
            file_name=file_name,
            mime='text/csv',
        )

# All Data 다운로드
if all_data:
    start_datetime = datetime.strptime(f"{selected_date} {start_time}", "%Y-%m-%d %H:%M:%S")
    end_datetime = start_datetime + timedelta(hours=3)

    # 각 job의 데이터를 하나의 DataFrame으로 병합
    combined_df = pd.DataFrame()
    for job, df in all_data.items():
        df = df.rename(columns={"value": job})
        if combined_df.empty:
            combined_df = df[['timestamp', job]]
        else:
            combined_df = pd.merge(combined_df, df[['timestamp', job]], on='timestamp', how='outer')

    # 정렬 및 NaN 값을 0으로 채움
    combined_df = combined_df.sort_values(by='timestamp').fillna(0)

    # CSV 데이터를 문자열로 변환
    csv_data = combined_df.to_csv(index=False)

    # 파일 이름 간소화
    start_str = start_datetime.strftime("%H")
    end_str = end_datetime.strftime("%H")
    all_file_name = f"{selected_date}_{start_str}T{end_str}_{query}.csv"

    # CSV 다운로드 버튼
    st.download_button(
        label=f"Download All Data for {selected_date}",
        data=csv_data,
        file_name=all_file_name,
        mime="text/csv",
    )
else:
    st.info("No data available for All Data download.")


# Streamlit UI: Command Sender
st.title("Command Sender")

# UID 선택 (Prometheus 데이터에서 추출한 Job 사용)
uid = st.selectbox("Select UID", jobs) if jobs else st.text_input("Enter UID", value="A000001")

# 명령어 선택
selected_command = st.selectbox("Select Command", list(COMMANDS.keys()))

# 추가 값 입력 (필요 시)
if "<value>" in COMMANDS[selected_command]:
    value = st.text_input("Enter Value", value="")
else:
    value = ""

# 요청 데이터 생성
request_payload = {
    "uid": uid,
    "type": "control",
    "command": selected_command,
    "value": value
}

st.write(f"Generated Request Payload: {request_payload}")

# 전송 버튼 클릭 시 실행
if st.button("Send Command"):
    response_data = None  # 이전 응답 초기화
    is_waiting_for_response = True  # 응답 대기 상태 설정

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_IP, SERVER_PORT))
        client_socket.sendall(json.dumps(request_payload).encode("utf-8"))
        threading.Thread(target=receive_response, args=(client_socket,), daemon=True).start()
        st.info("Command sent! Waiting for response...")
    except Exception as e:
        st.error(f"Failed to connect to server: {e}")
        is_waiting_for_response = False

# 서버 응답 처리
if response_data:
    if response_data.get("status") == "success":
        st.success("Command executed successfully!")
        st.json(response_data)
    else:
        st.error(f"Error: {response_data.get('error')}")