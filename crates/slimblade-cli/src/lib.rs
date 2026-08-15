use slimblade_image::{
    FirmwareIdentity, OFFICIAL_V449, RECOVERY_CARRIER, RECOVERY_GUARD, RECOVERY_STUB,
    RESET_TRAMPOLINE, STARTUP_TRAMPOLINE, USB_RECOVERY_PROBE, V449_DESCRIPTOR_PROBE,
};

pub const FULL_RECOVERY_CONFIRMATION: &str = "ERASE-MARKER-RESET";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FlashArtifact {
    OfficialV449,
    DescriptorProbe,
    RecoveryCarrier,
    ResetTrampoline,
    RecoveryStub,
    StartupTrampoline,
    RecoveryGuard,
    UsbRecoveryProbe,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PostFlashExpectation {
    Application { bcd_device: &'static str },
    ResidentLoader,
    UsbSilence,
}

impl FlashArtifact {
    #[must_use]
    pub const fn identity(self) -> FirmwareIdentity {
        match self {
            Self::OfficialV449 => OFFICIAL_V449,
            Self::DescriptorProbe => V449_DESCRIPTOR_PROBE,
            Self::RecoveryCarrier => RECOVERY_CARRIER,
            Self::ResetTrampoline => RESET_TRAMPOLINE,
            Self::RecoveryStub => RECOVERY_STUB,
            Self::StartupTrampoline => STARTUP_TRAMPOLINE,
            Self::RecoveryGuard => RECOVERY_GUARD,
            Self::UsbRecoveryProbe => USB_RECOVERY_PROBE,
        }
    }

    #[must_use]
    pub fn confirmation_matches(self, confirmation: &str) -> bool {
        digest_matches_hex(self.identity().container_sha256, confirmation)
    }

    #[must_use]
    pub fn confirmation_sha256(self) -> String {
        digest_to_hex(self.identity().container_sha256)
    }

    #[must_use]
    pub const fn post_flash_expectation(self) -> PostFlashExpectation {
        match self {
            Self::OfficialV449 => PostFlashExpectation::Application { bcd_device: "0449" },
            Self::DescriptorProbe => PostFlashExpectation::Application { bcd_device: "0450" },
            Self::RecoveryCarrier => PostFlashExpectation::Application { bcd_device: "0451" },
            Self::ResetTrampoline => PostFlashExpectation::Application { bcd_device: "0452" },
            Self::StartupTrampoline => PostFlashExpectation::Application { bcd_device: "0453" },
            Self::RecoveryStub => PostFlashExpectation::ResidentLoader,
            Self::RecoveryGuard => PostFlashExpectation::UsbSilence,
            Self::UsbRecoveryProbe => PostFlashExpectation::Application { bcd_device: "0454" },
        }
    }
}

#[must_use]
pub fn full_recovery_confirmation_matches(confirmation: &str) -> bool {
    confirmation == FULL_RECOVERY_CONFIRMATION
}

fn digest_matches_hex(digest: [u8; 32], confirmation: &str) -> bool {
    let bytes = confirmation.as_bytes();
    if bytes.len() != 64 {
        return false;
    }
    digest.into_iter().enumerate().all(|(index, byte)| {
        let offset = index * 2;
        bytes.get(offset).copied() == Some(hex_digit(byte >> 4_u8))
            && bytes.get(offset + 1).copied() == Some(hex_digit(byte & 0x0f))
    })
}

fn digest_to_hex(digest: [u8; 32]) -> String {
    let mut output = String::with_capacity(64);
    for byte in digest {
        output.push(char::from(hex_digit(byte >> 4_u8)));
        output.push(char::from(hex_digit(byte & 0x0f)));
    }
    output
}

const fn hex_digit(nibble: u8) -> u8 {
    if nibble < 10 {
        b'0' + nibble
    } else {
        b'a' + nibble - 10
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn carrier_flash_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RecoveryCarrier.confirmation_matches("wrong"));
    }

    #[test]
    fn reset_trampoline_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::ResetTrampoline.confirmation_matches("wrong"));
    }

    #[test]
    fn recovery_stub_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RecoveryStub.confirmation_matches("wrong"));
    }

    #[test]
    fn startup_trampoline_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::StartupTrampoline.confirmation_matches("wrong"));
    }

    #[test]
    fn recovery_guard_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::RecoveryGuard.confirmation_matches("wrong"));
        assert!(FlashArtifact::RecoveryGuard.confirmation_matches(
            "7bb3055bc1575bcb9ca4eab9ba2a83a3dbaba131e92cca78fffb18397cc2d19a"
        ));
    }

    #[test]
    fn full_recovery_needs_exact_action_confirmation() {
        assert!(!full_recovery_confirmation_matches("wrong"));
        assert!(full_recovery_confirmation_matches("ERASE-MARKER-RESET"));
    }

    #[test]
    fn usb_probe_needs_exact_hash_confirmation() {
        assert!(!FlashArtifact::UsbRecoveryProbe.confirmation_matches("wrong"));
        assert!(FlashArtifact::UsbRecoveryProbe.confirmation_matches(
            "d08395311afb43a289b05bbd0fb31a750c62371e957eedde4c08f0e7c78560e8"
        ));
    }
}
