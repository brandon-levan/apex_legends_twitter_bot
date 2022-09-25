##FROM public.ecr.aws/lambda/python:3.7
FROM python:3.7

COPY requirements.txt ./
RUN  pip install -r requirements.txt
COPY final.py ./

CMD [ "python", "./final.py"]