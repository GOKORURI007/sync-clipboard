{
  description = ''
    A extremely simple cross-platform clipboard synchronization tool using WebSockets.
    Note: On Linux, it depends on xclip or xsel (in x11), or wl-clipboard (in wayland).
    https://github.com/GOKORURI007/sync-clipboard
  '';

  inputs = {
    nixpkgs.url = "nixpkgs";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python311;
      # 把当前目录当 Python 包构建
      sync-clipboard = python.pkgs.buildPythonApplication rec {
        pname = "sync-clipboard";
        version = "0.3.0";
        src = ./.;

        format = "pyproject"; # 使用 pyproject.toml

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

        meta.mainProgram = "sync-clipboard"; # 让 nix run 知道主命令
      };
    in
    {
      packages.${system} = {
        default = sync-clipboard;
      };

      apps.${system}.default = {
        type = "app";
        program = "${sync-clipboard}/bin/sync-clipboard";
      };
    };
}
