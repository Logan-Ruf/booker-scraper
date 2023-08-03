FROM public.ecr.aws/lambda/python:3.11

WORKDIR /var/task

# Install wget and unzip
RUN yum install -y wget unzip

# Install libraries for Chrome and ChromeDriver binaries
RUN yum install -y wget unzip \
    libX11 libX11-devel libxcb libxcb-devel \
    atk atk-devel at-spi2-atk at-spi2-atk-devel \
    cups-libs libdrm libdbus xkbcommon at-spi2-core \
    libXcomposite libXdamage libXext libXfixes libXrandr mesa-libgbm \
    pango pango-devel cairo cairo-devel alsa-lib libxkbcommon

# Download and install Google Chrome
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/115.0.5790.170/linux64/chrome-linux64.zip
RUN unzip chrome-linux64.zip -d ${LAMBDA_TASK_ROOT}
RUN chmod +rx ${LAMBDA_TASK_ROOT}/chrome-linux64/*

# Download and install ChromeDriver
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/115.0.5790.170/linux64/chromedriver-linux64.zip
RUN unzip chromedriver-linux64.zip -d ${LAMBDA_TASK_ROOT}
RUN chmod +rx ${LAMBDA_TASK_ROOT}/chromedriver-linux64/*

# Cleanup
RUN rm chromedriver-linux64.zip chrome-linux64.zip

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]