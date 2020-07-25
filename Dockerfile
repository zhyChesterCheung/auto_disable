FROM hub.agoralab.co/uap/tools/python3
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY start_main.py ./
COPY load_write_mysql.py ./

ENTRYPOINT ["python3"]
CMD ["start_main.py"]