{ pkgs, lib, ... }:

{
  packages = [
    pkgs.just
    pkgs.graphviz

  ]
  ++ lib.optionals pkgs.stdenv.isDarwin (
    [ pkgs.zlib pkgs.xz ]
  );

  enterShell = ''
    which bencher
    [[ $? != 0 ]] && curl --proto '=https' --tlsv1.2 -sSfL https://bencher.dev/download/install-cli.sh | sh
  '';

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
    version = "3.14";
  };

  languages.rust = {
    channel = "stable";
    enable = true;
    components = [ "rustc" "cargo" "clippy" "rustfmt" "rust-analyzer" ];
  };

}
