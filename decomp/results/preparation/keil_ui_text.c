/* Read standard Win32 UI text for local diagnostics; no licensing internals.
 * Output is private input to keil_license_check.py, never a user-facing log.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static void list_products(HWND window)
{
    DWORD pid = 0;
    DWORD_PTR count = 0;
    HANDLE process;
    void *remote;
    BOOL wow64 = FALSE;
    GetWindowThreadProcessId(window, &pid);
    process = OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ |
                          PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (!process) return;
    /* This pinned MDK UI is 32-bit. LVM_GETITEMTEXT requires a buffer in the
     * receiving process; only column 0 (product) is read, never the LIC column.
     * No executable code or licensing state is inspected or modified.
     */
    if (!IsWow64Process(process, &wow64) || !wow64) { CloseHandle(process); return; }
    remote = VirtualAllocEx(process, NULL, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remote || (uintptr_t)remote > UINT32_MAX - 4096) { CloseHandle(process); return; }
    SendMessageTimeoutA(window, 0x1004, 0, 0, SMTO_ABORTIFHUNG, 1000, &count);
    for (DWORD_PTR row = 0; row < count && row < 16; ++row) {
        uint32_t item[16] = {0};
        char text[512] = {0};
        item[2] = 0; /* iSubItem: product column only */
        item[5] = (uint32_t)((uintptr_t)remote + 512);
        item[6] = sizeof(text) - 1;
        if (!WriteProcessMemory(process, remote, item, sizeof(item), NULL)) break;
        SendMessageTimeoutA(window, 0x102d, row, (LPARAM)remote,
                            SMTO_ABORTIFHUNG, 1000, NULL);
        if (ReadProcessMemory(process, (char *)remote + 512, text, sizeof(text) - 1, NULL))
            printf("PRODUCT\tSysListView32\t%s\036", text);
    }
    VirtualFreeEx(process, remote, 0, MEM_RELEASE);
    CloseHandle(process);
}

static BOOL CALLBACK child(HWND window, LPARAM unused)
{
    char text[4096] = {0}, cls[128] = {0};
    (void)unused;
    if (!IsWindowVisible(window)) return TRUE;
    GetClassNameA(window, cls, sizeof(cls));
    if (GetDlgCtrlID(window) == 1002 && strcmp(cls, "SysListView32") == 0)
        list_products(window);
    SendMessageTimeoutA(window, WM_GETTEXT, sizeof(text), (LPARAM)text,
                        SMTO_ABORTIFHUNG, 1000, NULL);
    /* Separate controls with a record delimiter, including multiline text. */
    printf("%u\t%s\t%s\036", (unsigned)GetDlgCtrlID(window), cls, text);
    return TRUE;
}

static BOOL CALLBACK top(HWND window, LPARAM unused)
{
    char title[512] = {0}, cls[128] = {0};
    DWORD pid = 0;
    GetWindowThreadProcessId(window, &pid);
    if (pid != (DWORD)unused || !IsWindowVisible(window)) return TRUE;
    GetClassNameA(window, cls, sizeof(cls));
    GetWindowTextA(window, title, sizeof(title));
    if (strcmp(cls, "#32770") != 0 && strcmp(title, "License Management") != 0) return TRUE;
    printf("TOP\t%p\t%s\036", (void *)window, title);
    EnumChildWindows(window, child, 0);
    return TRUE;
}

struct search { int id; HWND result; };
static BOOL CALLBACK find_child(HWND window, LPARAM opaque)
{
    struct search *query = (struct search *)opaque;
    if (IsWindowVisible(window) && GetDlgCtrlID(window) == query->id) {
        query->result = window;
        return FALSE;
    }
    return TRUE;
}

static HWND control(HWND parent, int id)
{
    struct search query = {id, NULL};
    EnumChildWindows(parent, find_child, (LPARAM)&query);
    return query.result;
}

int main(int argc, char **argv)
{
    HWND window = FindWindowA(NULL, "License Management");
    DWORD pid = 0;
    if (!window) return 2;
    if (argc == 4 && strcmp(argv[1], "install") == 0) {
        char key[256] = {0};
        DWORD used = 0;
        HWND edit = control(window, atoi(argv[2]));
        HWND button = control(window, atoi(argv[3]));
        HANDLE input;
        if (!edit || !button) return 3;
        input = CreateFileA("Z:\\license.txt", GENERIC_READ, FILE_SHARE_READ,
                            NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (input == INVALID_HANDLE_VALUE) return 4;
        if (!ReadFile(input, key, sizeof(key) - 1, &used, NULL)) {
            CloseHandle(input);
            return 5;
        }
        CloseHandle(input);
        while (used && (key[used-1] == '\n' || key[used-1] == '\r')) key[--used] = 0;
        if (!used || used >= sizeof(key) - 1) return 6;
        if (!SendMessageTimeoutA(edit, WM_SETTEXT, 0, (LPARAM)key,
                                 SMTO_ABORTIFHUNG, 2000, NULL)) return 7;
        SecureZeroMemory(key, sizeof(key));
        if (!IsWindowEnabled(button)) return 8;
        PostMessageA(button, BM_CLICK, 0, 0);
        return 0;
    }
    GetWindowThreadProcessId(window, &pid);
    EnumWindows(top, (LPARAM)pid);
    return 0;
}
