def configure_tx_chains(txChains, streamNum, mcsIdx):
    txChains = txChains.lower()

    RATE_MCS_ANT_A_MSK = 0x04000
    RATE_MCS_ANT_B_MSK = 0x08000
    RATE_MCS_ANT_C_MSK = 0x10000
    RATE_MCS_HT_MSK    = 0x00100

    mask = 0x0
    usedAntNum = 0

    if "a" in txChains:
        mask |= RATE_MCS_ANT_A_MSK
        usedAntNum += 1
    if "b" in txChains:
        mask |= RATE_MCS_ANT_B_MSK
        usedAntNum += 1
    if "c" in txChains:
        mask |= RATE_MCS_ANT_C_MSK
        usedAntNum += 1

    mask |= RATE_MCS_HT_MSK

    if streamNum > usedAntNum:
        print("Cannot use {} streams with {} antennas".format(streamNum, usedAntNum))
        print("Set stream num to {}".format(usedAntNum))
        streamNum = usedAntNum

    mcsMask = mcsIdx
    if streamNum == 2:
        mcsMask += 8
    elif streamNum == 3:
        mcsMask += 16

    mask |= mcsMask

    mask = "0x{:05x}".format(mask)
    print("Set TX mask: ", mask)

    filePath = "/sys/kernel/debug/iwlwifi/0000:03:00.0/iwldvm/debug/monitor_tx_rate"
    f = open(filePath, 'w')
    f.write(mask)
    f.close()

def configure_rx_chains(rxChains):
    rxChains = rxChains.lower()
    mask = 0x0
    aMask = 0x1
    bMask = 0x2
    cMask = 0x4

    if "a" in rxChains:
        mask |= aMask
    if "b" in rxChains:
        mask |= bMask
    if "c" in rxChains:
        mask |= cMask

    mask = "0x{:01x}".format(mask)
    print("Set RX chain mask: ", mask)

    filePath = "/sys/kernel/debug/iwlwifi/0000:03:00.0/iwldvm/debug/rx_chains_msk"
    f = open(filePath, 'w')
    f.write(mask)
    f.close()