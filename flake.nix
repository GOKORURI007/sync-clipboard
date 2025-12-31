{
  description = ''
    A extremely simple cross-platform clipboard synchronization tool using WebSockets.
    Note: On Linux, it depends on xclip or xsel (in x11), or wl-clipboard (in wayland).
    https://github.com/GOKORURI007/sync-clipboard
  '';

  inputs = {
    nixpkgs.url = "nixpkgs";
  };

  outputs = {self, nixpkgs}:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: import nixpkgs {inherit system;};
      pyproject = builtins.fromTOML (builtins.readFile ./pyproject.toml);
      version = pyproject.project.version;

      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python311;
    in
    {
      packages = forAllSystems(
      system:
              let
          pkgs = pkgsFor system;
          pythonPkgs = pkgs.python3Packages;
          deps = with pythonPkgs; [
            websockets
            click
            pyperclip
          ];
        in
         {
            default = python.pkgs.buildPythonApplication rec {
        pname = "sync-clipboard";
        version = "0.1.0";
        src = ./.;

        format = "pyproject";

        nativeBuildInputs = with python.pkgs; [
          setuptools
          wheel
        ];

        propagatedBuildInputs = with python.pkgs; [
          click
          pyperclip
          websockets
          customtkinter
          pystray
        ];

            meta.mainProgram = "sync-clipboard";   # 让 nix run 知道主命令
            };
        };
      );

      apps.${system}.default = {
        type = "app";
        program = "${sync-clipboard}/bin/sync-clipboard";
      };
    };
}