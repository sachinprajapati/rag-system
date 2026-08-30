FROM ghcr.io/prefix-dev/pixi:0.77.1

WORKDIR /app

# Copy the manifest first so Docker can reuse the dependency layer when only
# application code changes.
COPY pyproject.toml ./

RUN pixi install

COPY src ./src

EXPOSE 8000

CMD ["pixi", "run", "app"]
