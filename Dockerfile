FROM python:3.12-slim
WORKDIR /app
COPY agentharness ./agentharness
COPY benchmarks ./benchmarks
COPY configs ./configs
RUN useradd --create-home runner && mkdir /app/results && chown runner:runner /app/results
USER runner
ENTRYPOINT ["python", "-m", "agentharness"]
CMD ["demo", "--trusted-local", "--output", "/app/results/demo"]
