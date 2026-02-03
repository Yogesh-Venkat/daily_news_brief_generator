FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm config set fetch-retries 5 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-retry-maxtimeout 120000 \
 && npm install --prefer-offline --no-audit


COPY . .

EXPOSE 3000

CMD ["npm", "start"]
