from libspec import UserStory


class ServerBmcInstall(UserStory):
    """USER-STORY: SERVER-BMC-INSTALL

    An operator attaches a small TetronOS Server ISO to a machine through its
    BMC virtual media and installs it remotely, with no one at the keyboard.

    Priority: high (v1).
    User journey: attach ISO via BMC -> boot on serial or BMC KVM -> unattended
    or TUI install to disk -> reboot -> the machine is on the tetron mesh.
    Acceptance: verified in VMs first, then on pizzabox through its BMC
    (milestone M9). The ISO stays under the Server size budget.
    """
    brief_title = "Remote install of Server edition via BMC"
    priority = "high"


class RegularFullInstall(UserStory):
    """USER-STORY: REGULAR-FULL-INSTALL

    A user boots the Regular edition live ISO, tries it, and installs a fully
    provisioned TetronOS: kmscon console, tetron-wm desktop, the whole app
    suite, tetron mesh, all hardware firmware, offline.

    Priority: high (end goal, follows v1).
    Acceptance: milestones R0 to R3.
    """
    brief_title = "Fully provisioned Regular edition"
    priority = "high"


class LiveTry(UserStory):
    """USER-STORY: LIVE-TRY

    Anyone can boot the ISO live from USB or virtual media into tetron-wm
    without installing anything.

    Priority: medium.
    Acceptance: live boot assertions pass in BIOS and UEFI VMs.
    """
    brief_title = "Try live without installing"
    priority = "medium"
