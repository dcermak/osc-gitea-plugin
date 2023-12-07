import osc.commandline


class GiteaCloneCommand(osc.commandline.OscCommand):
    name = "clone"

    def init_arguments(self) -> None:
        self.add_argument("package", type=str, nargs=1, help="The package to clone")

    def run(self, args) -> None:
        from osc.core import checkout_package
        from osc_gitea_plugin.common import API_URL, fetch_devel_pkg

        devel = fetch_devel_pkg(args.package[0])
        checkout_package(API_URL, devel.devel_prj, devel.devel_pkg)
