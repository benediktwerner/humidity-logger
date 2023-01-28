#!/bin/bash
if [[ $EUID > 0 ]]; then  
  echo "Please run as root/sudo"
  exit 1
fi

HOME_DIR=$(eval echo ~${SUDO_USER:-${USER}})
CURRENT_USER="${SUDO_USER:-${USER}}"
DEFAULT_USER="wernerfamily"

SCRIPT_URL="https://raw.githubusercontent.com/gauravpathak/humidity-logger/master/logger.py"
SERVICE_URL="https://raw.githubusercontent.com/gauravpathak/humidity-logger/master/humidity-logger.service"
CONFIG_URL="https://raw.githubusercontent.com/gauravpathak/humidity-logger/master/config.toml.example"

GRAFANA_DATA_SRC_FILE="influxdb-datasource.yaml"
GRAFANA_DATA_SRC_URL="https://raw.githubusercontent.com/gauravpathak/humidity-logger/setup-script/influxdb-datasource.yaml.example"
CONFIG_FILE="${CONFIG_URL##*/}"
SAMPLING_PERIOD=5 #seconds
INFLUX_TOKEN=""
INFLUX_HOST="localhost"
INFLUX_PORT=8086
INFLUX_ORG=""
INFLUX_BUCKET=""

INFLUX_CLIENT_TAR="influxdb2-client-2.6.1-linux-arm64.tar.gz"
INFLUX_CLIENT_URL="https://dl.influxdata.com/influxdb/releases/${INFLUX_CLIENT_TAR}"
INFLUX_DEB_PACKAGE="influxdb2-2.6.1-arm64.deb"
INFLUX_DEB_URL="https://dl.influxdata.com/influxdb/releases/${INFLUX_DEB_PACKAGE}"
WGET="/usr/bin/wget"

SENSE_HAT="sense-hat"
PYTHON3_PIP="python3-pip"

INFLUX_DB_INSTALL_STATUS=$(dpkg-query --status "${INFLUX_DEB_PACKAGE%%-*}" | grep Status)
SENSE_HAT_INSTALL_STATUS=$(dpkg-query --status "${SENSE_HAT}" | grep Status)
PYTHON3_PIP_INSTALL_STATUS=$(dpkg-query --status "${PYTHON3_PIP}" | grep Status)
JQ_INSTALL_STATUS=$(dpkg-query --status jq | grep Status)

if [[ ! "$JQ_INSTALL_STATUS" == *"install ok installed"* ]]; then
    apt install -y jq
fi

if [[ ! "$INFLUX_DB_INSTALL_STATUS" == *"install ok installed"* ]]; then
    ${WGET} -4 ${INFLUX_CLIENT_URL}
    tar -xvf "${INFLUX_CLIENT_TAR}"
    cp -vf "${INFLUX_CLIENT_TAR%%.tar*}/influx" "/usr/bin/"
    rm -rf "${INFLUX_CLIENT_TAR}" "${INFLUX_CLIENT_TAR%%.tar*}"
    
    ${WGET} -4 ${INFLUX_DEB_URL}
    dpkg -i "${INFLUX_DEB_PACKAGE}"
    systemctl daemon-reload
    systemctl enable influxdb
    systemctl start influxdb
    rm -f "${INFLUX_DEB_PACKAGE}"
    influx setup
fi

if [[ ! "$SENSE_HAT_INSTALL_STATUS" == *"install ok installed"* ]]; then
    apt install -y "${SENSE_HAT}"
fi
if [[ ! "$PYTHON3_PIP_INSTALL_STATUS" == *"install ok installed"* ]]; then
    apt install -y "${PYTHON3_PIP}"
fi


mkdir -p "${HOME_DIR}/humidity-logger"
# Force IPv4 for wget command using -4 flag
${WGET} -4 "${SCRIPT_URL}" --directory-prefix="${HOME_DIR}/humidity-logger/"
${WGET} -4 "${SERVICE_URL}" --directory-prefix="${HOME_DIR}/humidity-logger/"
${WGET} -4 "${CONFIG_URL}" --directory-prefix="${HOME_DIR}/humidity-logger/"
mv "${HOME_DIR}/humidity-logger/${CONFIG_FILE}" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"

# Insert current Username in service file
sed -i "s/${DEFAULT_USER}/${CURRENT_USER}/g" "${HOME_DIR}/humidity-logger/${SERVICE_URL##*/}"
cp -fv "${HOME_DIR}/humidity-logger/humidity-logger.service" "/etc/systemd/system/"
chown -v "root:root" "/etc/systemd/system/humidity-logger.service"

read -p "Room name:" ROOM_NAME

INFLUX_TOKEN=$(influx auth ls --json | jq '.[] | .token')
INFLUX_ORG=$(influx org ls --json | jq '.[]|.name')
INFLUX_BUCKET=$(influx bucket ls --json | jq '.[0] |.name')

sed -i "s/%roomname%/${ROOM_NAME}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"
sed -i "s/%samplingperiod%/${SAMPLING_PERIOD}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"
sed -i "s/%influxtoken%/${INFLUX_TOKEN}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"
sed -i "s/%influxhost%/${INFLUX_HOST}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"
sed -i "s/%influxport%/${INFLUX_PORT}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"
sed -i "s/%influxorg%/${INFLUX_ORG}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"
sed -i "s/%influxbucket%/${INFLUX_BUCKET}/g" "${HOME_DIR}/humidity-logger/${CONFIG_FILE%.*}"

# Grafana Setup 
GRAFANA_PKG="grafana"
GRAFANA_KEY_STATUS=$(apt-key list 2> /dev/null | grep "${GRAFANA_PKG}")
GRAFANA_INSTALL_STATUS=$(dpkg-query --status "${GRAFANA_PKG}" | grep Status)
if [[ ! $GRAFANA_KEY_STATUS ]]; then
    wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
    echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
    apt update
fi

if [[ ! "$GRAFANA_INSTALL_STATUS" == *"install ok installed"* ]]; then
    apt install -y "${GRAFANA_PKG}"
    systemctl daemon-reload
    systemctl enable grafana-server
    systemctl start grafana-server
fi

${WGET} -4 "${GRAFANA_DATA_SRC_URL}" -O "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}"
sed -i "s/%influxtoken%/${INFLUX_TOKEN}/g" "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}"
sed -i "s/%influxhost%/${INFLUX_HOST}/g" "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}"
sed -i "s/%influxport%/${INFLUX_PORT}/g" "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}"
sed -i "s/%influxorg%/${INFLUX_ORG}/g" "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}"
sed -i "s/%influxbucket%/${INFLUX_BUCKET}/g" "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}"
mv "${HOME_DIR}/humidity-logger/${GRAFANA_DATA_SRC_FILE}" "/etc/grafana/provisioning/datasources/"

systemctl stop grafana-server
systemctl start grafana-server

systemctl enable humidity-logger
systemctl stop humidity-logger
systemctl start humidity-logger
