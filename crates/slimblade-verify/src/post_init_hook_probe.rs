use core::fmt;

use slimblade_image::{
    APPLICATION_HEADER_OFFSET, POST_INIT_HOOK_PROBE, POST_INIT_HOOK_PROBE_ARTIFACT,
    STACK_HEADER_OFFSET, STARTUP_TRAMPOLINE, V449_BCD_DEVICE_OFFSET, parse_header,
    refresh_header_crc, sha256,
};

use crate::{
    ArmAddress, BranchError, ThumbAddress, decode_arm_branch, decode_thumb_bl,
    elf::{ELF_MACHINE_ARM, ELF_TYPE_EXECUTABLE, Elf32},
    encode_arm_b, encode_thumb_bl,
};

const INJECTION_START: usize = 0x21ac;
const INJECTION_END: usize = 0x2300;
const RESET_BRANCH: usize = 0x2064;
const TRAMPOLINE: u32 = 0x22cc;
const MODE_BRANCH: usize = 0x19c00;
const LOCAL_BRANCH: usize = 0x19c6e;
const LOCAL_CALL: usize = 0x197cc;
const HOOK: u32 = 0x22c0;
const MAIN_LOOP: u32 = 0x19bf2;

const DISPATCH: [u8; 18] = [
    0x0d, 0x28, 0x04, 0xd0, 0x0e, 0x28, 0x04, 0xd0, 0x0f, 0x28, 0x0b, 0xd0, 0x70, 0x47, 0x2c, 0x4b,
    0x18, 0x47,
];
const ARM_AND_QUERY: [u8; 26] = [
    0x10, 0xb5, 0x00, 0xf0, 0x0a, 0xf8, 0x2a, 0x48, 0x03, 0x21, 0x01, 0x70, 0xa3, 0x20, 0xe0, 0x70,
    0x10, 0xbd, 0x27, 0x48, 0x00, 0x78, 0xe0, 0x70, 0x70, 0x47,
];
const HOOK_BYTES: [u8; 12] = [
    0x02, 0x20, 0x20, 0x70, 0x00, 0x48, 0x00, 0x47, 0xf3, 0x9b, 0x01, 0x00,
];
const CRITICAL_WORDS: [(usize, u32); 13] = [
    (0x0c0, 0x0001_895d),
    (0x0c4, 0x0040_0282),
    (0x0c8, 0x0080_3000),
    (0x0cc, 0x0000_807c),
    (0x0d0, 0x7856_3412),
    (0x0d4, 0x0000_807d),
    (0x0d8, 0x19d2_bc9a),
    (0x0dc, 0x0001_78eb),
    (0x0e0, 0x0080_001c),
    (0x0e4, 0x0000_22e8),
    (0x0e8, 0x0080_6000),
    (0x0ec, 0x0000_58a9),
    (0x0f0, 0x0000_a958),
];

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Error {
    BaseIdentity,
    InjectionSize { actual: usize },
    InjectionIdentity,
    Layout,
    Branch(BranchError),
    DerivedImage,
    Bytes { offset: usize },
    Word { offset: usize, actual: u32 },
    Header,
    ContainerIdentity,
    Elf,
}

impl fmt::Display for Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BaseIdentity => formatter.write_str("base is not exact v4.53"),
            Self::InjectionSize { actual } => write!(formatter, "injection is {actual} bytes"),
            Self::InjectionIdentity => formatter.write_str("injection identity changed"),
            Self::Layout => formatter.write_str("image layout is truncated"),
            Self::Branch(error) => write!(formatter, "branch: {error}"),
            Self::DerivedImage => formatter.write_str("image is not the exact derived candidate"),
            Self::Bytes { offset } => write!(formatter, "bytes changed at {offset:#x}"),
            Self::Word { offset, actual } => {
                write!(
                    formatter,
                    "word at injection +{offset:#x} is {actual:#010x}"
                )
            },
            Self::Header => formatter.write_str("container header audit failed"),
            Self::ContainerIdentity => formatter.write_str("container identity changed"),
            Self::Elf => formatter.write_str("ELF geometry changed"),
        }
    }
}

impl core::error::Error for Error {}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Report {
    pub injection_sha256: [u8; 32],
    pub container_sha256: [u8; 32],
    pub payload_sha256: [u8; 32],
    pub payload_crc: u32,
}

/// Builds the dormant, marker-armed post-initialization hook candidate.
///
/// # Errors
///
/// Returns an error unless both inputs have their reviewed identities and every patched range
/// exists.
pub fn build(base: &[u8], injection: &[u8]) -> Result<Vec<u8>, Error> {
    STARTUP_TRAMPOLINE
        .validate(base)
        .map_err(|_| Error::BaseIdentity)?;
    if injection.len() != INJECTION_END - INJECTION_START {
        return Err(Error::InjectionSize {
            actual: injection.len(),
        });
    }
    if !POST_INIT_HOOK_PROBE_ARTIFACT.code_matches(injection) {
        return Err(Error::InjectionIdentity);
    }

    require_base(base, MODE_BRANCH, &[0xf7, 0xd1])?;
    require_base(base, 0x19c6d, &[0x0a, 0x00, 0x00])?;
    require_base(base, 0x197cb, &[0x0a, 0x00, 0x00, 0x00, 0x00])?;

    let mut image = base.to_vec();
    replace(&mut image, INJECTION_START, injection)?;
    replace(
        &mut image,
        RESET_BRANCH,
        &encode_arm_b(
            ArmAddress::new(u32::try_from(RESET_BRANCH).map_err(|_| Error::Layout)?)
                .map_err(Error::Branch)?,
            ArmAddress::new(TRAMPOLINE).map_err(Error::Branch)?,
        )
        .map_err(Error::Branch)?,
    )?;

    replace(&mut image, MODE_BRANCH, &[0x35, 0xd1])?;
    replace(&mut image, LOCAL_BRANCH - 1, &[0x00, 0xad, 0xe5])?;
    replace(&mut image, 0x197cb, &[0x00])?;
    replace(
        &mut image,
        LOCAL_CALL,
        &encode_thumb_bl(
            ThumbAddress::new(u32::try_from(LOCAL_CALL).map_err(|_| Error::Layout)?)
                .map_err(Error::Branch)?,
            ThumbAddress::new(HOOK).map_err(Error::Branch)?,
        )
        .map_err(Error::Branch)?,
    )?;
    *image.get_mut(V449_BCD_DEVICE_OFFSET).ok_or(Error::Layout)? = 0x59;
    refresh_header_crc(&mut image, APPLICATION_HEADER_OFFSET).map_err(|_| Error::Header)?;
    refresh_header_crc(&mut image, STACK_HEADER_OFFSET).map_err(|_| Error::Header)?;
    Ok(image)
}

/// Audits the complete candidate, including its dormant stock branch chain and marker-first arm.
///
/// # Errors
///
/// Returns the first failed identity, byte, branch, header, or ELF invariant.
pub fn verify(
    base: &[u8],
    image: &[u8],
    injection: &[u8],
    elf_bytes: &[u8],
) -> Result<Report, Error> {
    if image != build(base, injection)? {
        return Err(Error::DerivedImage);
    }
    require(injection, 0, &DISPATCH)?;
    require(injection, 0x12, &ARM_AND_QUERY)?;
    require(injection, 0x114, &HOOK_BYTES)?;
    for (offset, expected) in CRITICAL_WORDS {
        let actual = read_u32(injection, offset)?;
        if actual != expected {
            return Err(Error::Word { offset, actual });
        }
    }
    if injection.get(0xf4..0x114) != Some([0_u8; 0x20].as_slice()) {
        return Err(Error::Bytes { offset: 0xf4 });
    }
    verify_branch_chain(image)?;
    if image.get(0x2300..0x2330) != base.get(0x2300..0x2330) {
        return Err(Error::Bytes { offset: 0x2300 });
    }
    if image.get(0x18f9a..0x18fbe) != base.get(0x18f9a..0x18fbe) {
        return Err(Error::Bytes { offset: 0x18f9a });
    }
    for offset in [STACK_HEADER_OFFSET, APPLICATION_HEADER_OFFSET] {
        let header = parse_header(image, offset).map_err(|_| Error::Header)?;
        if !header.crc_is_valid(image).map_err(|_| Error::Header)? {
            return Err(Error::Header);
        }
    }
    verify_elf(elf_bytes)?;
    let payload = POST_INIT_HOOK_PROBE
        .validate(image)
        .map_err(|_| Error::ContainerIdentity)?;
    Ok(Report {
        injection_sha256: sha256(injection),
        container_sha256: sha256(image),
        payload_sha256: sha256(payload),
        payload_crc: slimblade_protocol::updater_crc32(payload),
    })
}

fn verify_branch_chain(image: &[u8]) -> Result<(), Error> {
    require(image, MODE_BRANCH, &[0x35, 0xd1])?;
    require(image, LOCAL_BRANCH - 1, &[0x00, 0xad, 0xe5])?;
    require(image, 0x197cb, &[0x00])?;
    let target = decode_thumb_bl(
        read_array(image, LOCAL_CALL)?,
        ThumbAddress::new(u32::try_from(LOCAL_CALL).map_err(|_| Error::Layout)?)
            .map_err(Error::Branch)?,
    )
    .map_err(Error::Branch)?;
    if target.get() != HOOK {
        return Err(Error::Bytes { offset: LOCAL_CALL });
    }
    if read_u32(image, 0x22c8)? != MAIN_LOOP | 1 {
        return Err(Error::Bytes { offset: 0x22c8 });
    }
    let (_, reset_target) = decode_arm_branch(
        read_array(image, RESET_BRANCH)?,
        ArmAddress::new(u32::try_from(RESET_BRANCH).map_err(|_| Error::Layout)?)
            .map_err(Error::Branch)?,
    )
    .map_err(Error::Branch)?;
    if reset_target.get() != TRAMPOLINE {
        return Err(Error::Bytes {
            offset: RESET_BRANCH,
        });
    }
    Ok(())
}

fn verify_elf(bytes: &[u8]) -> Result<(), Error> {
    let elf = Elf32::parse(bytes).map_err(|_| Error::Elf)?;
    if elf.elf_type() != ELF_TYPE_EXECUTABLE
        || elf.machine() != ELF_MACHINE_ARM
        || elf.entry() != TRAMPOLINE
    {
        return Err(Error::Elf);
    }
    let mut geometry = Vec::new();
    for section in elf.sections() {
        let section = section.map_err(|_| Error::Elf)?;
        if section.is_relocation() || section.is_writable_allocated() {
            return Err(Error::Elf);
        }
        if section.is_allocated_executable() {
            geometry.push((section.name, section.address, section.size));
        }
    }
    if geometry
        != [
            (".carrier", 0x21ac, 0x0f4),
            (".probe", 0x22c0, 0x00c),
            (".trampoline", 0x22cc, 0x034),
        ]
    {
        return Err(Error::Elf);
    }
    Ok(())
}

fn replace(bytes: &mut [u8], offset: usize, replacement: &[u8]) -> Result<(), Error> {
    bytes
        .get_mut(offset..offset.saturating_add(replacement.len()))
        .ok_or(Error::Layout)?
        .copy_from_slice(replacement);
    Ok(())
}

fn require_base(bytes: &[u8], offset: usize, expected: &[u8]) -> Result<(), Error> {
    require(bytes, offset, expected).map_err(|_| Error::BaseIdentity)
}

fn require(bytes: &[u8], offset: usize, expected: &[u8]) -> Result<(), Error> {
    if bytes.get(offset..offset.saturating_add(expected.len())) == Some(expected) {
        Ok(())
    } else {
        Err(Error::Bytes { offset })
    }
}

fn read_array(bytes: &[u8], offset: usize) -> Result<[u8; 4], Error> {
    bytes
        .get(offset..offset.saturating_add(4))
        .ok_or(Error::Layout)?
        .try_into()
        .map_err(|_| Error::Layout)
}

fn read_u32(bytes: &[u8], offset: usize) -> Result<u32, Error> {
    Ok(u32::from_le_bytes(read_array(bytes, offset)?))
}

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "tests mutate bounded generated fixtures and expect audited results"
)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::*;

    struct Fixtures {
        base: Vec<u8>,
        injection: Vec<u8>,
        container: Vec<u8>,
        elf: Vec<u8>,
    }

    fn read_if_present(path: PathBuf) -> Option<Vec<u8>> {
        path.exists()
            .then(|| std::fs::read(path).expect("read post-init hook fixture"))
    }

    fn fixtures() -> Option<Fixtures> {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let target = root.join("firmware/bk3635-stock-harness/target");
        Some(Fixtures {
            base: read_if_present(root.join(
                "firmware/startup_trampoline/build/DO_NOT_FLASH-stock-startup-trampoline.container.bin",
            ))?,
            injection: read_if_present(target.join(
                "post-init-hook/DO_NOT_FLASH-post-init-hook-probe.injection.bin",
            ))?,
            container: read_if_present(target.join(
                "post-init-hook/DO_NOT_FLASH-post-init-hook-probe.container.bin",
            ))?,
            elf: read_if_present(
                target.join("thumbv5te-none-eabi/release/slimblade-post-init-hook-probe"),
            )?,
        })
    }

    #[test]
    fn exact_candidate_rebuilds_and_passes() {
        let Some(data) = fixtures() else { return };
        assert_eq!(
            build(&data.base, &data.injection),
            Ok(data.container.clone())
        );
        let report = verify(&data.base, &data.container, &data.injection, &data.elf)
            .expect("audit exact post-init hook probe");
        assert_eq!(report.payload_crc, 0x8065_29df);
    }

    #[test]
    fn arm_is_after_the_marker_call() {
        let Some(data) = fixtures() else { return };
        let marker_call = decode_thumb_bl(
            read_array(&data.injection, 0x14).expect("marker call"),
            ThumbAddress::new(0x21c0).expect("call address"),
        )
        .expect("decode marker call");
        assert_eq!(marker_call.get(), 0x21d8);
        assert_eq!(&data.injection[0x18..0x22], &ARM_AND_QUERY[6..16]);
    }

    #[test]
    fn changed_injection_and_branch_are_rejected() {
        let Some(mut data) = fixtures() else { return };
        data.injection[0x114] ^= 1;
        assert_eq!(
            build(&data.base, &data.injection),
            Err(Error::InjectionIdentity)
        );

        let Some(mut data) = fixtures() else { return };
        data.container[MODE_BRANCH] ^= 1;
        assert_eq!(
            verify(&data.base, &data.container, &data.injection, &data.elf),
            Err(Error::DerivedImage)
        );
    }
}
