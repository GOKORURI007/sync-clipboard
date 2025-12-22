{
  description = "Synchronizing the clipboard between different OS via WebSocket";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages = {
          sync-clipboard = pkgs.python313Packages.buildPythonApplication {
            pname = "sync-clipboard";
            version = "0.1.0";
            src = ./.;
            pyproject = true;

            nativeBuildInputs = with pkgs.python313Packages; [
              setuptools
              wheel
            ];

            propagatedBuildInputs = with pkgs.python313Packages; [
              websockets
              click
              pyperclip
              customtkinter
            ];

            # Make sure the main script is executable
            postInstall = ''
              install -Dm755 main.py $out/bin/sync-clipboard
            '';

            pythonImportsCheck = [ "sync-clipboard" ];
          };

          default = self.packages.${system}.sync-clipboard;
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            pkgs.python313
            pkgs.python313Packages.pip
            pkgs.python313Packages.setuptools
            pkgs.python313Packages.wheel
            pkgs.python313Packages.websockets
            pkgs.python313Packages.click
            pkgs.python313Packages.pyperclip
            pkgs.python313Packages.customtkinter
          ];

          # Set up environment variables if needed
          SYNC_CLIPBOARD_ENV = "development";
        };
      });
}