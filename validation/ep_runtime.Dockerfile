# Optional experiment image, not an API/deployment image. Build with --network none.
# Context: the verified directory emitted by validation.ep_sources prepare.
# xgboost-runtime passed; reference-candidate is intentionally NOT a working runtime
# yet (curl development headers missing; see docs/EP_RUNTIME.md).
FROM rocker/r-ver@sha256:fb487cf8a2029fc1dbc17621cf41ac913d49ac74a1ff9e27bf9bbc982e55d08d AS xgboost-runtime
ENV MAKEFLAGS=-j2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
COPY jsonlite_2.0.0.tar.gz data.table_1.18.6.1.tar.gz xgboost-src-3.4.2.tar.gz /opt/ep-sources/
RUN echo '887344a4c87300b3756614a2c403f6e00b0ad95ddd3b671dcbe0e8e9a1103841  /opt/ep-sources/jsonlite_2.0.0.tar.gz' | sha256sum -c - \
 && echo 'a6fd2ab26667e3be013417e5d3d89b99d6775b6a799114c1064ffdc70f842d93  /opt/ep-sources/data.table_1.18.6.1.tar.gz' | sha256sum -c - \
 && echo 'd7de76bdaf48e9e0bc84b27c0c42f15f3d831e624d102d6c019bab7027b3cabd  /opt/ep-sources/xgboost-src-3.4.2.tar.gz' | sha256sum -c -
# Retain complete upstream sources/notices in this local-only experiment image.
RUN R CMD INSTALL /opt/ep-sources/jsonlite_2.0.0.tar.gz \
 && R CMD INSTALL /opt/ep-sources/data.table_1.18.6.1.tar.gz
RUN tar -xzf /opt/ep-sources/xgboost-src-3.4.2.tar.gz -C /opt/ep-sources \
 && R CMD INSTALL /opt/ep-sources/xgboost/R-package
RUN Rscript --vanilla -e 'stopifnot(getRversion() == "4.6.1", packageVersion("xgboost") == "3.4.2.1", packageVersion("jsonlite") == "2.0.0", packageVersion("data.table") == "1.18.6.1")'
FROM xgboost-runtime AS reference-candidate
COPY . /opt/ep-runtime/
RUN cd /opt/ep-runtime && sha256sum -c sources.sha256 \
 && Rscript --vanilla /opt/ep-runtime/ep_install.R
