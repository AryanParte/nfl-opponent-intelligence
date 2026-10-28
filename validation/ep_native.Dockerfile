# Appended to the existing, pinned xgboost-runtime stage by ep_native.prepare.
# This is an offline experiment build, not a deployment or production image.
FROM xgboost-runtime AS full-reference
ENV TZ=UTC
COPY . /opt/ep-runtime/
RUN cd /opt/ep-runtime && sha256sum -c sources.sha256 \
 && Rscript --vanilla /opt/ep-runtime/ep_native_install.R \
 && Rscript --vanilla /opt/ep-runtime/ep_install.R
