import pytest

from app.domain.entities import Cpf
from app.domain.exceptions import CpfInvalidoError


def test_cpf_valido_normaliza_e_formata():
    cpf = Cpf("529.982.247-25")
    assert cpf.digitos == "52998224725"
    assert cpf.formatado == "529.982.247-25"
    assert cpf.mascarado == "***.982.247-**"


@pytest.mark.parametrize("valor", ["", "123", "111.111.111-11", "529.982.247-26", "abc"])
def test_cpf_invalido(valor):
    with pytest.raises(CpfInvalidoError):
        Cpf(valor)
