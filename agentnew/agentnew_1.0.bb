DESCRIPTION = "Comminication handler app for Vestel EVC04 Project"
SECTION = "apps"
DEPENDS = ""
LICENSE = "CLOSED"
S = "${WORKDIR}"
FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI = "file://agent.py \
           file://agent.service \
           file://definitions.py \
           file://configuration_manager.py \
           file://drive_green_manager.py \
           file://system.db \
           file://acpw_update.bin \
           file://webconfig.db \
           file://bluetooth_handler.py \
           file://Bluetooth_Server.py \
           file://BTClassic_Server.py \
           file://BLE_Server.py \
           file://ble_transceiver.py \
           file://example_advertisement.py \
           file://example_gatt_server.py \
           file://gpio_controller.py \
           file://root-CA.crt \
           file://logging.conf \
           file://otaCert.crt \
           file://agent.db \
           file://signatureCert.crt \
"

FILES_${PN} = "/usr/lib/vestel/agent.py \
               /usr/lib/vestel/definitions.py \
               /usr/lib/vestel/configuration_manager.py \
               /usr/lib/vestel/drive_green_manager.py \
               /usr/lib/vestel/bluetooth_handler.py \
               /usr/lib/vestel/Bluetooth_Server.py \
               /usr/lib/vestel/BTClassic_Server.py \
               /usr/lib/vestel/BLE_Server.py \
               /usr/lib/vestel/ble_transceiver.py \
               /usr/lib/vestel/example_advertisement.py \
               /usr/lib/vestel/example_gatt_server.py \
               /usr/lib/vestel/gpio_controller.py \
               /usr/lib/vestel/system.db \
               /usr/lib/vestel/acpw_update.bin \
               /usr/lib/vestel/webconfig.db \
               /usr/lib/vestel/root-CA.crt \
               /usr/lib/vestel/logging.conf \
               /usr/lib/vestel/otaCert.crt \
               /usr/lib/vestel/agent.db \
               /usr/lib/vestel/signatureCert.crt \
"

inherit systemd

DEPENDS += "zeromq"

do_install() {
    install -d ${D}/usr/lib/vestel

    cp ${WORKDIR}/agent.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/definitions.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/configuration_manager.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/drive_green_manager.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/bluetooth_handler.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/Bluetooth_Server.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/BTClassic_Server.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/BLE_Server.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/ble_transceiver.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/example_advertisement.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/example_gatt_server.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/gpio_controller.py ${D}/usr/lib/vestel
    cp ${WORKDIR}/system.db ${D}/usr/lib/vestel
    cp ${WORKDIR}/acpw_update.bin ${D}/usr/lib/vestel
    cp ${WORKDIR}/webconfig.db ${D}/usr/lib/vestel
    cp ${WORKDIR}/root-CA.crt ${D}/usr/lib/vestel
    cp ${WORKDIR}/logging.conf ${D}/usr/lib/vestel
    cp ${WORKDIR}/otaCert.crt ${D}/usr/lib/vestel
    cp ${WORKDIR}/agent.db ${D}/usr/lib/vestel
    cp ${WORKDIR}/signatureCert.crt ${D}/usr/lib/vestel

    chmod 700 ${D}/usr/lib/vestel/agent.py
    chmod 700 ${D}/usr/lib/vestel/definitions.py
    chmod 700 ${D}/usr/lib/vestel/configuration_manager.py
    chmod 700 ${D}/usr/lib/vestel/drive_green_manager.py
    chmod 700 ${D}/usr/lib/vestel/bluetooth_handler.py
    chmod 700 ${D}/usr/lib/vestel/Bluetooth_Server.py
    chmod 700 ${D}/usr/lib/vestel/BTClassic_Server.py
    chmod 700 ${D}/usr/lib/vestel/BLE_Server.py
    chmod 700 ${D}/usr/lib/vestel/ble_transceiver.py
    chmod 700 ${D}/usr/lib/vestel/example_advertisement.py
    chmod 700 ${D}/usr/lib/vestel/example_gatt_server.py
    chmod 700 ${D}/usr/lib/vestel/gpio_controller.py
    chmod 700 ${D}/usr/lib/vestel/system.db
    chmod 700 ${D}/usr/lib/vestel/acpw_update.bin
    chmod 700 ${D}/usr/lib/vestel/webconfig.db
    chmod 700 ${D}/usr/lib/vestel/root-CA.crt
    chmod 700 ${D}/usr/lib/vestel/logging.conf
    chmod 700 ${D}/usr/lib/vestel/otaCert.crt
    chmod 700 ${D}/usr/lib/vestel/agent.db
    chmod 700 ${D}/usr/lib/vestel/signatureCert.crt

    install -d ${D}/etc/systemd/system
    install -m 700 ${WORKDIR}/agent.service ${D}/etc/systemd/system
}

SYSTEMD_SERVICE_${PN} = "agent.service"
SYSTEMD_AUTO_ENABLE_${PN} = "enable"
