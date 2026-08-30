FROM ghcr.io/prefix-dev/pixi:0.77.1

WORKDIR /app

# Keep Node.js and npm inside the Pixi environment.
COPY pixi.toml package.json package-lock.json ./

RUN pixi run install

COPY . .

EXPOSE 3000

CMD ["pixi", "run", "app"]
