# S03 proposed read-only counter interface v1

This is the firmware contract to be implemented by the assembly supplier; it is not a claim that firmware exists or is deployed. Host I2C7-bit address0x42,<=100kHz, isolated from field bus. Counter acquisition continues locally while the Pi reads. Source publication period<=100ms; host rejects age/heartbeat>200ms or unexplained resets.

The only allowed write selects register0x00 for a subsequent read. No actuator, reset, configuration or equipment-control writes are provided. A read returns one atomic48-byte little-endian snapshot; a partially read frame or failed CRC is invalid. Do not mix live bytes from different snapshots.

| Offset | Type | Field |
|---|---|---|
|0x00|4 ASCII bytes|CRPC magic|
|0x04|uint8|protocol1|
|0x05|uint8|status:0invalid,1valid|
|0x06|uint16|frame length48|
|0x08|uint64|new boot identifier each MCU restart|
|0x10|uint64|source monotonic time in microseconds|
|0x18|uint32|publication sequence, modulo2^32|
|0x1C|uint32|accepted rising-edge count, modulo2^32|
|0x20|uint16|line voltage / actual pullup supply, scaled0..65535|
|0x22|uint16|reserved0|
|0x24|uint32|configured publication interval in microseconds,<=100000|
|0x28|uint32|firmware revision identifier; full source hash in configuration|
|0x2C|uint32|CRC32 IEEE over preceding44bytes|

Preserve the remote10k EOL/2.2k series/4.7k pullup network. Count only qualified LOW/HIGH window transitions. Both stable HIGH and stable LOW can be valid zero frequency. Open/short/missing EOL/miswire produce INVALID, not healthy zero. Capture capability>=5kHz must be factory-tested. A stuck Hall switch cannot be detected solely from a static valid level; reviewed process-response/current/voltage checks must catch missing response after command.

Host records receive-monotonic time, source timestamp, boot identifier, sequence, count and quality. Clock offset, transport time and scheduling jitter enter the reported uncertainty; source and host clocks are not assumed synchronized. Use>=2s rolling flow windows, report pulse quantization, and qualify actual freshness/timing on the delivered assembly. MCU has no execution authority.
