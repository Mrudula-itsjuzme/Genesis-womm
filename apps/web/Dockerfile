FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG CORE_API_URL=http://core-api:8000
ENV CORE_API_URL=$CORE_API_URL
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
