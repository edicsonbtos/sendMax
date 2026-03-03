FROM node:22-alpine

# Establecer directorio de trabajo
WORKDIR /app

# Copiar package.json y package-lock.json
COPY package.json package-lock.json ./

# Forzar la instalación normal de todas las dependencias (Cache Busted)
ARG CACHE_BUST=1
RUN npm install

# Copiar el resto del código
COPY . .

# Variables de entorno por defecto (se sobreescriben en Railway)
ENV NEXT_PUBLIC_API_URL=https://sendmax11-production.up.railway.app
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Ejecutar el build de Next.js
RUN npm run build

# Exponer el puerto
EXPOSE 3000

# Comando para iniciar la aplicación (Railway inyecta el $PORT)
CMD ["npm", "start"]
