#![no_std]

use core::fmt;

pub const APPLICATION_PAYLOAD_OFFSET: u32 = 0x2000;
pub const NORMAL_REPORT_ID: u8 = 0x08;
pub const NORMAL_REPORT_LENGTH: usize = 17;
pub const BOOT_REPORT_ID: u8 = 0x06;
pub const BOOT_REPORT_LENGTH: usize = 49;
pub const DOWNLOAD_BLOCK_LENGTH: usize = 32;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct UsbIdentity {
    pub vendor_id: u16,
    pub product_id: u16,
}

pub const KENSINGTON_WIRED_IDENTITY: UsbIdentity = UsbIdentity {
    vendor_id: 0x047d,
    product_id: 0x80d7,
};
pub const BOOT_IDENTITIES: [UsbIdentity; 3] = [
    UsbIdentity {
        vendor_id: 0x25a7,
        product_id: 0xfabe,
    },
    UsbIdentity {
        vendor_id: 0x3554,
        product_id: 0xf600,
    },
    UsbIdentity {
        vendor_id: 0x3554,
        product_id: 0xf800,
    },
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NormalReport([u8; NORMAL_REPORT_LENGTH]);

impl NormalReport {
    /// Parses and validates a normal-mode report.
    ///
    /// # Errors
    ///
    /// Returns an error if the report has the wrong length, report ID, or checksum.
    #[allow(
        clippy::indexing_slicing,
        reason = "the exact report length is checked before the fixed report-ID byte is indexed"
    )]
    pub fn parse(bytes: &[u8]) -> Result<Self, ReportParseError> {
        if bytes.len() != NORMAL_REPORT_LENGTH {
            return Err(ReportParseError::WrongLength {
                expected: NORMAL_REPORT_LENGTH,
                actual: bytes.len(),
            });
        }
        if bytes[0] != NORMAL_REPORT_ID {
            return Err(ReportParseError::WrongReportId {
                expected: NORMAL_REPORT_ID,
                actual: bytes[0],
            });
        }
        if !checksum_is_valid(bytes) {
            return Err(ReportParseError::InvalidChecksum);
        }
        let mut report = [0; NORMAL_REPORT_LENGTH];
        report.copy_from_slice(bytes);
        Ok(Self(report))
    }

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

    #[must_use]
    pub const fn command_byte(self) -> u8 {
        self.0[1]
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BootReport([u8; BOOT_REPORT_LENGTH]);

impl BootReport {
    /// Parses and validates a bootloader-mode report.
    ///
    /// # Errors
    ///
    /// Returns an error if the report has the wrong length or report ID.
    #[allow(
        clippy::indexing_slicing,
        reason = "the exact report length is checked before the fixed report-ID byte is indexed"
    )]
    pub fn parse(bytes: &[u8]) -> Result<Self, ReportParseError> {
        if bytes.len() != BOOT_REPORT_LENGTH {
            return Err(ReportParseError::WrongLength {
                expected: BOOT_REPORT_LENGTH,
                actual: bytes.len(),
            });
        }
        if bytes[0] != BOOT_REPORT_ID {
            return Err(ReportParseError::WrongReportId {
                expected: BOOT_REPORT_ID,
                actual: bytes[0],
            });
        }
        let mut report = [0; BOOT_REPORT_LENGTH];
        report.copy_from_slice(bytes);
        Ok(Self(report))
    }

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

    /// Constructs a bootloader download packet for one payload block.
    ///
    /// # Errors
    ///
    /// Returns an error if `offset` is outside the payload or cannot be represented by the
    /// bootloader's 32-bit address field.
    #[allow(
        clippy::indexing_slicing,
        reason = "offset and block bounds are checked before copying into fixed packet fields"
    )]
    pub fn download(payload: &[u8], offset: usize) -> Result<Self, PacketError> {
        if offset >= payload.len() {
            return Err(PacketError::PayloadOffset {
                offset,
                payload_length: payload.len(),
            });
        }
        let Ok(address_offset) = u32::try_from(offset) else {
            return Err(PacketError::AddressOverflow);
        };
        let address = APPLICATION_PAYLOAD_OFFSET
            .checked_add(address_offset)
            .ok_or(PacketError::AddressOverflow)?;
        let remaining = payload.len() - offset;
        let data_length = remaining.min(DOWNLOAD_BLOCK_LENGTH);
        let Ok(data_length_u8) = u8::try_from(data_length) else {
            return Err(PacketError::AddressOverflow);
        };
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

    #[must_use]
    pub const fn command_byte(self) -> u8 {
        self.0[1]
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReportParseError {
    WrongLength { expected: usize, actual: usize },
    WrongReportId { expected: u8, actual: u8 },
    InvalidChecksum,
}

impl fmt::Display for ReportParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::WrongLength { expected, actual } => {
                write!(f, "expected {expected}-byte report, got {actual}")
            },
            Self::WrongReportId { expected, actual } => {
                write!(f, "expected report ID {expected:#04x}, got {actual:#04x}")
            },
            Self::InvalidChecksum => f.write_str("report checksum is invalid"),
        }
    }
}

impl core::error::Error for ReportParseError {}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PacketError {
    PayloadOffset {
        offset: usize,
        payload_length: usize,
    },
    AddressOverflow,
}

impl fmt::Display for PacketError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PayloadOffset {
                offset,
                payload_length,
            } => write!(
                f,
                "payload offset {offset} is outside {payload_length}-byte image"
            ),
            Self::AddressOverflow => f.write_str("payload address exceeds 32 bits"),
        }
    }
}

impl core::error::Error for PacketError {}

#[must_use]
#[allow(
    clippy::indexing_slicing,
    reason = "the const loop condition proves every indexed byte is within the slice"
)]
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
#[allow(
    clippy::indexing_slicing,
    reason = "the const loop condition proves every indexed byte is within the slice"
)]
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
#[allow(
    clippy::as_conversions,
    clippy::indexing_slicing,
    reason = "the const loop proves indexing; u8-to-u32 is lossless and const From is not stable"
)]
pub const fn updater_crc32(bytes: &[u8]) -> u32 {
    let mut crc = u32::MAX;
    let mut byte_index = 0;
    while byte_index < bytes.len() {
        crc ^= bytes[byte_index] as u32;
        let mut bit = 0_u32;
        while bit < 8_u32 {
            crc = if crc & 1 == 1 {
                (crc >> 1_u32) ^ 0xedb8_8320
            } else {
                crc >> 1_u32
            };
            bit += 1_u32;
        }
        byte_index += 1;
    }
    crc
}

#[cfg(test)]
#[allow(
    clippy::cast_possible_truncation,
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "tests use fixed vectors and expect success as part of each assertion"
)]
mod tests {
    use super::*;

    #[test]
    fn known_boot_identities_match_python() {
        assert!(BOOT_IDENTITIES.contains(&UsbIdentity {
            vendor_id: 0x25a7,
            product_id: 0xfabe,
        }));
        assert!(BOOT_IDENTITIES.contains(&UsbIdentity {
            vendor_id: 0x3554,
            product_id: 0xf600,
        }));
        assert!(BOOT_IDENTITIES.contains(&UsbIdentity {
            vendor_id: 0x3554,
            product_id: 0xf800,
        }));
    }

    #[test]
    fn normal_report_parser_accepts_only_valid_checksummed_reports() {
        let report = NormalReport::command(0x0e);
        assert_eq!(NormalReport::parse(report.as_bytes()), Ok(report));

        let mut bad_checksum = *report.as_bytes();
        bad_checksum[16] ^= 1;
        assert_eq!(
            NormalReport::parse(&bad_checksum),
            Err(ReportParseError::InvalidChecksum)
        );
        assert!(matches!(
            NormalReport::parse(&report.as_bytes()[..16]),
            Err(ReportParseError::WrongLength { .. })
        ));
        let mut wrong_id = *report.as_bytes();
        wrong_id[0] = BOOT_REPORT_ID;
        assert!(matches!(
            NormalReport::parse(&wrong_id),
            Err(ReportParseError::WrongReportId { .. })
        ));
    }

    #[test]
    fn boot_report_parser_enforces_length_and_report_id() {
        let report = BootReport::query();
        assert_eq!(BootReport::parse(report.as_bytes()), Ok(report));
        assert!(matches!(
            BootReport::parse(&report.as_bytes()[..48]),
            Err(ReportParseError::WrongLength { .. })
        ));
        let mut wrong_id = *report.as_bytes();
        wrong_id[0] = NORMAL_REPORT_ID;
        assert!(matches!(
            BootReport::parse(&wrong_id),
            Err(ReportParseError::WrongReportId { .. })
        ));
    }

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
            *byte = if index == 255 {
                0xff
            } else {
                u8::try_from(index).expect("fixture index fits in one byte")
            };
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
        let payload: [u8; 64] = core::array::from_fn(|index| {
            u8::try_from(index).expect("fixture index fits in one byte")
        });
        let report = BootReport::download(&payload, 0).expect("valid first block");
        assert_eq!(&report.as_bytes()[..4], &[0x06, 0xb1, 0xc0, 0x20]);
        assert_eq!(&report.as_bytes()[5..9], &[0, 0, 0x20, 0]);
        assert_eq!(&report.as_bytes()[17..], &payload[..32]);
    }

    #[test]
    fn short_final_download_packet_is_ff_padded() {
        let payload: [u8; 35] = core::array::from_fn(|index| {
            u8::try_from(index).expect("fixture index fits in one byte")
        });
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
