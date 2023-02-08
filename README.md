# VXAI



## Getting started
- install python v3.7
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install python3.7
sudo apt install python3.7-distutils
```


- start with the following command:
```
sudo apt-get install libomp-dev
```

```
uvicorn app.main:app --reload
gunicorn app.main:app -k uvicorn.workers.UvicornWorker
```

- horror movie about a girl in captivity

## Clone
- ``


## Deployment
- pip install gunicorn
- scp sql_app.db root@68.183.142.111:/root/


## Kill process
- lsof -i:8000
- kill -9 <PID>