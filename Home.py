import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json

# 타이틀 설정
st.title("요양병원 Data View")

# 사용자 입력 UI
query = st.text_input("Enter Prometheus Query:", "radar_v2_range")
selected_date = st.date_input("Select a Date")
start_time = st.selectbox("Select Start Time", [f"{str(i).zfill(2)}:00:00" for i in range(0, 24, 3)])
step = st.number_input("Step (in seconds):", min_value=1, value=10, step=1)

# API URL
url = "https://3iztvmb7bj.execute-api.ap-northeast-2.amazonaws.com/prometheus/v1/query_range"

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
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    job_data = {}
    if data.get('status') == 'success':
        results = data['data']['result']
        for result in results:
            job = result['metric']['job']
            if "room" in job:
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
        start_str = start_datetime.strftime("%H%M")
        end_str = end_datetime.strftime("%H%M")
        file_name = f"{selected_date}_{start_str}T{end_str}_{step}_{selected_job}_{query}.csv"
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
    start_str = start_datetime.strftime("%H%M")
    end_str = end_datetime.strftime("%H%M")
    all_file_name = f"{selected_date}_{start_str}T{end_str}_{step}.csv"

    # CSV 다운로드 버튼
    st.download_button(
        label=f"Download All Data for {selected_date}",
        data=csv_data,
        file_name=all_file_name,
        mime="text/csv",
    )
else:
    st.info("No data available for All Data download.")
