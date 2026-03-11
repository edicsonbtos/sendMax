FROM node:22-alpine AS builder

# Argumentos de build para inyectar variables de entorno en el bundle de Next.js
# Railway debe pasar este ARG en build settings
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-https://sendmax11-production.up.railway.app}

WORKDIR /app

# Copiar package.json y package-lock.json
COPY package.json package-lock.json ./

# Instalación reproducible con npm ci (no npm install)
RUN npm ci

# Copiar el resto del código
COPY . .

# Variables de entorno de build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Ejecutar el build de Next.js
RUN npm run build

# --- Stage 2: Runner ---
FROM node:22-alpine AS runner
WORKDIR /app

# Copy necessary files from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/public ./public

# Exponer el puerto
EXPOSE 3000

# Comando para iniciar la aplicación (Railway inyecta el $PORT)
CMD ["npm", "start"]
