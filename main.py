import uvicorn
from routers import app


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        port=5000,
        host='127.0.0.1',
        reload=True
    )
