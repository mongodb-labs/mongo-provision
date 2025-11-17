FROM ubuntu:20.04

RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    ca-certificates \
    git \
    curl \
    python3-pip \
    gcc python3-dev

# Clear out the package stuff for lightness.
RUN rm -rf /var/lib/apt/lists/*

# This OS’s latest Python is 3.8.10.
# That python’s latest compatible PyMongo is 4.10.1.
RUN pip3 install mtools[all]

RUN curl -fsSL https://raw.githubusercontent.com/aheckmann/m/master/bin/m > m.sh
RUN chmod +x m.sh

ENV PATH=$PATH:/root/.local/bin

COPY entrypoint.sh .

ENTRYPOINT ["./entrypoint.sh"]
