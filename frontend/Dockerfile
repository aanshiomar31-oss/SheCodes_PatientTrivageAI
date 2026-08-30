# ==============================================================================
# PatientTriage.ai — Frontend Dockerfile
# ==============================================================================
# Development-oriented image: runs the Vite dev server with hot module
# reload, matching how the backend Dockerfile runs uvicorn directly rather
# than a production ASGI server. A production build (multi-stage, served
# via nginx) is a deployment-hardening task for a later milestone.
FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
