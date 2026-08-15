#![no_std]
#![forbid(unsafe_code)]

use core::fmt;

pub const APPLICATION_PAYLOAD_OFFSET: u32 = 0x2000;
pub const NORMAL_REPORT_ID: u8 = 0x08;
pub const NORMAL_REPORT_LENGTH: usize = 17;
pub const BOOT_REPORT_ID: u8 = 0x06;
pub const BOOT_REPORT_LENGTH: usize = 49;
pub const DOWNLOAD_BLOCK_LENGTH: usize = 32;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NormalReport([u8; NORMAL_REPORT_LENGTH]);

impl NormalReport {
    /// Constructs a normal-mode command report.
    ///
    /// The command is a byte at the type boundary, so the Python implementation's
    /// out-of-range integer case cannot compile in Rust.
    ///
    /// ```compile_fail
    /// use slimblade_protocol::NormalReport;
    /// let _ = NormalReport::command(0x100);
    /// ```
    #[must_use]
    pub const fn command(command: u8) -> Self {
        let mut bytes = [0; NORMAL_REPORT_LENGTH];
        bytes[0] = NORMAL_REPORT_ID;
        bytes[1] = command;
        bytes[NORMAL_REPORT_LENGTH - 1] = checksum(&bytes);
        Self(bytes)
    }

    #[must_use]
    pub const fn reset_to_loader() -> Self {
        Self::command(0x0d)
    }

    #[must_use]
    pub const fn as_bytes(&self) -> &[u8; NORMAL_REPORT_LENGTH] {
        &self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BootReport([u8; BOOT_REPORT_LENGTH]);

impl BootReport {
    #[must_use]
    pub const fn command(command: u8) -> Self {
        let mut bytes = [0; BOOT_REPORT_LENGTH];
        bytes[0] = BOOT_REPORT_ID;
        bytes[1] = command;
        bytes[BOOT_REPORT_LENGTH - 1] = checksum(&bytes);
        Self(bytes)
    }

    #[must_use]
    pub const fn reset() -> Self {
        Self::command(0x0d)
    }

    #[must_use]
    pub const fn query() -> Self {
        Self::command(0xb2)
    }

    #[must_use]
    pub const fn prepare(payload_length: u32, payload_crc: u32) -> Self {
        let mut bytes = [0; BOOT_REPORT_LENGTH];
        bytes[0] = BOOT_REPORT_ID;
        bytes[1] = 0xb0;
        let length = payload_length.to_be_bytes();
        bytes[5] = length[0];
        bytes[6] = length[1];
        bytes[7] = length[2];
        bytes[8] = length[3];
        let crc = payload_crc.to_be_bytes();
        bytes[9] = crc[0];
        bytes[10] = crc[1];
        bytes[11] = crc[2];
        bytes[12] = crc[3];
        Self(bytes)
    }

    pub fn download(payload: &[u8], offset: usize) -> Result<Self, PacketError> {
        if offset >= payload.len() {
            return Err(PacketError::PayloadOffset {
                offset,
                payload_length: payload.len(),
            });
        }
        let address_offset = u32::try_from(offset).map_err(|_| PacketError::AddressOverflow)?;
        let address = APPLICATION_PAYLOAD_OFFSET
            .checked_add(address_offset)
            .ok_or(PacketError::AddressOverflow)?;
        let remaining = payload.len() - offset;
        let data_length = remaining.min(DOWNLOAD_BLOCK_LENGTH);
        let data_length_u8 = u8::try_from(data_length).map_err(|_| PacketError::AddressOverflow)?;
        let final_block = data_length == remaining;

        let mut bytes = [0; BOOT_REPORT_LENGTH];
        bytes[0] = BOOT_REPORT_ID;
        bytes[1] = 0xb1;
        bytes[2] = if final_block { 0xc1 } else { 0xc0 };
        bytes[3] = data_length_u8;
        let address = address.to_be_bytes();
        bytes[5..9].copy_from_slice(&address);
        bytes[17..].fill(0xff);
        bytes[17..17 + data_length].copy_from_slice(&payload[offset..offset + data_length]);
        Ok(Self(bytes))
    }

    #[must_use]
    pub const fn as_bytes(&self) -> &[u8; BOOT_REPORT_LENGTH] {
        &self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PacketError {
    PayloadOffset {
        offset: usize,
        payload_length: usize,
    },
    AddressOverflow,
}

impl fmt::Display for PacketError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PayloadOffset {
                offset,
                payload_length,
            } => write!(
                formatter,
                "payload offset {offset} is outside {payload_length}-byte image"
            ),
            Self::AddressOverflow => formatter.write_str("payload address exceeds 32 bits"),
        }
    }
}

#[must_use]
pub const fn checksum(bytes: &[u8]) -> u8 {
    let mut sum = 0_u8;
    let mut index = 0;
    while index < bytes.len() {
        sum = sum.wrapping_add(bytes[index]);
        index += 1;
    }
    0x55_u8.wrapping_sub(sum)
}

#[must_use]
pub const fn checksum_is_valid(bytes: &[u8]) -> bool {
    let mut sum = 0_u8;
    let mut index = 0;
    while index < bytes.len() {
        sum = sum.wrapping_add(bytes[index]);
        index += 1;
    }
    sum == 0x55
}

/// BK3635 updater CRC: reflected CRC-32 with an all-ones initial value and no
/// final XOR.
#[must_use]
pub const fn updater_crc32(bytes: &[u8]) -> u32 {
    let mut crc = u32::MAX;
    let mut byte_index = 0;
    while byte_index < bytes.len() {
        crc ^= bytes[byte_index] as u32;
        let mut bit = 0;
        while bit < 8 {
            crc = if crc & 1 == 1 {
                (crc >> 1) ^ 0xedb8_8320
            } else {
                crc >> 1
            };
            bit += 1;
        }
        byte_index += 1;
    }
    crc
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normal_reset_packet_matches_python() {
        assert_eq!(
            NormalReport::reset_to_loader().as_bytes(),
            &[0x08, 0x0d, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x40,]
        );
    }

    #[test]
    fn carrier_command_packets_match_python() {
        for (command, final_checksum) in [(0x0e, 0x3f), (0x0f, 0x3e), (0x10, 0x3d)] {
            let report = NormalReport::command(command);
            assert_eq!(report.as_bytes()[16], final_checksum);
            assert!(checksum_is_valid(report.as_bytes()));
        }
    }

    #[test]
    fn boot_reset_packet_matches_python() {
        let report = BootReport::reset();
        assert_eq!(&report.as_bytes()[..2], &[0x06, 0x0d]);
        assert_eq!(report.as_bytes()[48], 0x42);
        assert!(checksum_is_valid(report.as_bytes()));
    }

    #[test]
    fn boot_query_packet_matches_python() {
        let report = BootReport::query();
        assert_eq!(&report.as_bytes()[..2], &[0x06, 0xb2]);
        assert_eq!(report.as_bytes()[48], 0x9d);
        assert!(checksum_is_valid(report.as_bytes()));
    }

    #[test]
    fn updater_crc_vectors_match_python() {
        assert_eq!(updater_crc32(b""), 0xffff_ffff);
        assert_eq!(updater_crc32(b"123456789"), 0x340b_c6d9);
        let mut payload = [0_u8; 256];
        for (index, byte) in payload.iter_mut().enumerate() {
            *byte = if index == 255 { 0xff } else { index as u8 };
        }
        assert_eq!(updater_crc32(&payload), 0xd6fa_738c);
    }

    #[test]
    fn prepare_packet_matches_python() {
        let report = BootReport::prepare(256, 0xd6fa_738c);
        assert_eq!(&report.as_bytes()[..2], &[0x06, 0xb0]);
        assert_eq!(&report.as_bytes()[5..9], &[0, 0, 1, 0]);
        assert_eq!(&report.as_bytes()[9..13], &[0xd6, 0xfa, 0x73, 0x8c]);
    }

    #[test]
    fn nonfinal_download_packet_matches_python() {
        let payload: [u8; 64] = core::array::from_fn(|index| index as u8);
        let report = BootReport::download(&payload, 0).expect("valid first block");
        assert_eq!(&report.as_bytes()[..4], &[0x06, 0xb1, 0xc0, 0x20]);
        assert_eq!(&report.as_bytes()[5..9], &[0, 0, 0x20, 0]);
        assert_eq!(&report.as_bytes()[17..], &payload[..32]);
    }

    #[test]
    fn short_final_download_packet_is_ff_padded() {
        let payload: [u8; 35] = core::array::from_fn(|index| index as u8);
        let report = BootReport::download(&payload, 32).expect("valid final block");
        assert_eq!(&report.as_bytes()[..4], &[0x06, 0xb1, 0xc1, 0x03]);
        assert_eq!(&report.as_bytes()[5..9], &[0, 0, 0x20, 0x20]);
        assert_eq!(&report.as_bytes()[17..20], &payload[32..]);
        assert_eq!(&report.as_bytes()[20..], &[0xff; 29]);
    }

    #[test]
    fn download_rejects_offset_outside_payload() {
        assert_eq!(
            BootReport::download(&[1, 2, 3], 3),
            Err(PacketError::PayloadOffset {
                offset: 3,
                payload_length: 3,
            })
        );
    }
}
