/* Build-only recovery-path reconstruction. DO NOT FLASH IT. */

__attribute__((noreturn)) void bk3635_enter_resident_loader(void);

__attribute__((noreturn)) void stub_main(void)
{
    bk3635_enter_resident_loader();
}
