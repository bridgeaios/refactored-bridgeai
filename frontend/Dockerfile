FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev --no-audit --no-fund 2>/dev/null || npm install --omit=dev --no-audit --no-fund
COPY . ./
EXPOSE 3000
CMD ["node", "serve-no-cache.cjs"]
