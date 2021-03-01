FROM python:3.7
 
WORKDIR /srv
ADD . .
#for pymssql
ENV DB_CONN=10.0.0.4
ENV SNMP_DB_PORT=30008
ENV DB_PASSWORD=postgres
ENV SNMPDB=dxsnmp
ENV DB_USER=postgres
ENV API_PORT=80
ENV VALIDATE_API_URL=http://172.17.28.122:30000/token/validate
RUN pip install --upgrade pip
 
ENV DB_CONN=10.20.19.216
ENV SNMP_DB_PORT=30008
ENV DB_PASSWORD=postgres
ENV SNMPDB=dxsnmp
ENV DB_USER=postgres
ENV API_PORT=80
ENV VALIDATE_API_URL=https://10.20.19.216/snmp/token/validate
RUN pip install --upgrade pip

RUN apt-get update
RUN apt-get install vim -y

RUN pip install Flask==1.1.1
RUN pip install Flask-Cors==3.0.8
RUN pip install Flask-JWT==0.3.2
RUN pip install Flask-JWT-Extended==3.20.0
RUN pip install flask-marshmallow==0.10.1
RUN pip install Flask-RESTful==0.3.7
RUN pip install Flask-SQLAlchemy==2.4.0
RUN pip install marshmallow==3.0.0rc8
RUN pip install PyJWT==1.7.1
RUN pip install pyOpenSSL==19.0.0
RUN pip install scapy==2.4.3
RUN pip install pysnmp==4.4.12
RUN pip install requests==2.22.0
RUN pip install datetime==4.3
RUN pip install psutil==5.6.3
RUN pip install jinjasql==0.1.7
RUN pip install psycopg2==2.8.5

 
EXPOSE 80 
ADD . /srv
 
ENTRYPOINT [ "python" ] 
CMD [ "/srv/pollerapi.py" ]
