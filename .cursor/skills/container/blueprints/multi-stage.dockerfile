# BLUEPRINT: Multi-Stage Container Build
# STRUCTURAL: FROM stages, ARG injection, non-root ownership, COPY --from, layer cache ordering
# ILLUSTRATIVE: base images, app paths, build commands — replace with project specifics

# Stage 1: Build
# ILLUSTRATIVE: Replace with your runtime's build image (e.g. node:22-alpine, python:3.12-slim)
FROM node:22-alpine AS builder

# ILLUSTRATIVE: /app is conventional; adjust to your needs
WORKDIR /app

# STRUCTURAL: Copy dependency manifests before source — cache layer survives source-only changes
# ILLUSTRATIVE: Replace with your dependency files (requirements.txt, pom.xml, etc.)
COPY package.json package-lock.json ./
RUN npm ci

# STRUCTURAL: Source copied after deps so a code change doesn't invalidate the install layer
COPY . .

# STRUCTURAL: ARG forces explicit injection — no default prevents silent misconfiguration
# ILLUSTRATIVE: Replace BUILD_ENV with your required build-time variable name
ARG BUILD_ENV
RUN npm run build:${BUILD_ENV}

# Stage 2: Serve
# ILLUSTRATIVE: Replace with your production base image; never use :latest in production
FROM nginx:alpine AS runtime

# STRUCTURAL: Set file ownership to the nginx user so workers can read content under least privilege
# ILLUSTRATIVE: Replace /app/dist with your build output path
COPY --from=builder /app/dist /usr/share/nginx/html
RUN chown -R nginx:nginx /usr/share/nginx/html

# STRUCTURAL: nginx master must bind port 80 as root, then drops workers to the nginx user internally;
#             do not add a USER instruction here — for app servers (Node/Python/Java) that own the
#             process, create a dedicated user and set USER before CMD
EXPOSE 80

# ILLUSTRATIVE: Replace with your server's start command
CMD ["nginx", "-g", "daemon off;"]
