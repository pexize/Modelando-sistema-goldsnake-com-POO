from datetime import datetime
from colorama import Fore, Style
import re
import json
from abc import ABC, abstractmethod

# Classes Base
class Transacao(ABC):
    def __init__(self, valor: float):
        self.valor = valor
        self.data = datetime.now()

    @abstractmethod
    def registrar(self, conta):
        pass


class Deposito(Transacao):
    def registrar(self, conta):
        conta.depositar(self.valor)


class Saque(Transacao):
    def registrar(self, conta):
        conta.sacar(self.valor)


class Historico:
    def __init__(self):
        self.transacoes = []

    def adicionar_transacao(self, transacao):
        self.transacoes.append(transacao)

    def to_dict(self):
        return {
            "transacoes": [
                {"valor": t.valor, "data": t.data.isoformat()} for t in self.transacoes
            ]
        }

    @classmethod
    def from_dict(cls, data):
        historico = cls()
        historico.transacoes = [
            Deposito(float(t["valor"])) if t["valor"] > 0 else Saque(-float(t["valor"]))
            for t in data.get("transacoes", [])
        ]
        return historico


class Cliente:
    def __init__(self, endereco: str):
        self.endereco = endereco
        self.contas = []

    def adicionar_conta(self, conta):
        self.contas.append(conta)

    def realizar_transacao(self, conta, transacao):
        transacao.registrar(conta)

    def to_dict(self):
        return {"endereco": self.endereco, "contas": [c.numero for c in self.contas]}

    @classmethod
    def from_dict(cls, data):
        cliente = cls(data["endereco"])
        cliente.contas = data.get("contas", [])
        return cliente


class PessoaFisica(Cliente):
    def __init__(self, cpf: str, nome: str, data_nascimento: str, endereco: str):
        super().__init__(endereco)
        self.cpf = cpf
        self.nome = nome
        self.data_nascimento = data_nascimento

    def to_dict(self):
        return {
            "cpf": self.cpf,
            "nome": self.nome,
            "data_nascimento": self.data_nascimento,
            "endereco": self.endereco,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            cpf=data["cpf"],
            nome=data["nome"],
            data_nascimento=data["data_nascimento"],
            endereco=data["endereco"],
        )


class Conta:
    numero_conta_global = 1

    def __init__(self, cliente: Cliente, saldo: float = 0.0, agencia: str = "0001"):
        self._saldo = saldo
        self.agencia = agencia
        self.cliente = cliente
        self.numero = Conta.numero_conta_global
        Conta.numero_conta_global += 1
        self.historico = Historico()

    @property
    def saldo(self) -> float:
        return self._saldo

    def sacar(self, valor: float) -> bool:
        if valor > self._saldo or valor <= 0:
            print(f"{Fore.RED}❌ Valor inválido ou saldo insuficiente.{Style.RESET_ALL}")
            return False
        self._saldo -= valor
        self.historico.adicionar_transacao(Saque(valor))
        print(f"{Fore.GREEN}✅ Saque realizado com sucesso!{Style.RESET_ALL}")
        return True

    def depositar(self, valor: float) -> bool:
        if valor <= 0:
            print(f"{Fore.RED}❌ Valor inválido para depósito.{Style.RESET_ALL}")
            return False
        self._saldo += valor
        self.historico.adicionar_transacao(Deposito(valor))
        print(f"{Fore.GREEN}✅ Depósito realizado com sucesso!{Style.RESET_ALL}")
        return True

    def to_dict(self):
        return {
            "numero": self.numero,
            "cpf": self.cliente.cpf,
            "saldo": self._saldo,
            "historico": self.historico.to_dict(),
        }

    @classmethod
    def from_dict(cls, data, clientes):
        cliente = next((c for c in clientes if c.cpf == data["cpf"]), None)
        if not cliente:
            raise ValueError(f"Cliente com CPF {data['cpf']} não encontrado.")
        return cls(
            cliente=cliente,
            saldo=data.get("saldo", 0.0),
            agencia=data.get("agencia", "0001"),
        )


class ContaCorrente(Conta):
    def __init__(self, cliente: Cliente, saldo: float = 0.0, limite: float = 500.0, limite_saques: int = 3):
        super().__init__(cliente, saldo)
        self.limite = limite
        self.limite_saques = limite_saques

    def sacar(self, valor: float) -> bool:
        if self.limite_saques <= 0:
            print(f"{Fore.RED}❌ Limite de saques diários atingido.{Style.RESET_ALL}")
            return False
        if valor > (self._saldo + self.limite) or valor <= 0:
            print(f"{Fore.RED}❌ Valor inválido ou saldo insuficiente.{Style.RESET_ALL}")
            return False
        self._saldo -= valor
        self.limite_saques -= 1
        self.historico.adicionar_transacao(Saque(valor))
        print(f"{Fore.GREEN}✅ Saque realizado com sucesso!{Style.RESET_ALL}")
        return True

    def to_dict(self):
        return {
            "numero": self.numero,
            "cpf": self.cliente.cpf,
            "saldo": self._saldo,
            "limite": self.limite,
            "limite_saques": self.limite_saques,
            "historico": self.historico.to_dict(),
        }

    @classmethod
    def from_dict(cls, data, clientes):
        cliente = next((c for c in clientes if c.cpf == data["cpf"]), None)
        if not cliente:
            raise ValueError(f"Cliente com CPF {data['cpf']} não encontrado.")
        return cls(
            cliente=cliente,
            saldo=data.get("saldo", 0.0),
            limite=data.get("limite", 500.0),
            limite_saques=data.get("limite_saques", 3),
        )


# Funções Auxiliares
def validar_cpf(cpf: str) -> bool:
    return bool(re.match(r"^\d{11}$", cpf))


def carregar_dados():
    try:
        with open('banco_data.json', 'r') as file:
            data = json.load(file)
            usuarios = [PessoaFisica.from_dict(d) for d in data.get("usuarios", [])]
            contas = [ContaCorrente.from_dict(d, usuarios) for d in data.get("contas", [])]
            return usuarios, contas
    except FileNotFoundError:
        return [], []
    except json.JSONDecodeError:
        print(f"{Fore.RED}⚠️ Erro ao carregar os dados. Arquivo JSON inválido.{Style.RESET_ALL}")
        return [], []


def salvar_dados(usuarios, contas):
    data = {
        "usuarios": [u.to_dict() for u in usuarios],
        "contas": [c.to_dict() for c in contas],
    }
    with open('banco_data.json', 'w') as file:
        json.dump(data, file, indent=4)


def cadastrar_usuario(usuarios):
    print(f"{Fore.YELLOW}=== Cadastro de Usuário ==={Style.RESET_ALL}")
    nome = input("Nome: ")
    data_nascimento = input("Data de Nascimento (DD/MM/AAAA): ")
    cpf = input("CPF (11 dígitos): ")
    endereco = input("Endereço: ")

    if not validar_cpf(cpf):
        print(f"{Fore.RED}❌ CPF inválido. O CPF deve conter 11 dígitos numéricos.{Style.RESET_ALL}")
        return

    if any(u.cpf == cpf for u in usuarios):
        print(f"{Fore.RED}❌ Já existe um usuário cadastrado com esse CPF.{Style.RESET_ALL}")
        return

    usuario = PessoaFisica(cpf=cpf, nome=nome, data_nascimento=data_nascimento, endereco=endereco)
    usuarios.append(usuario)
    print(f"{Fore.GREEN}✅ Usuário {nome} cadastrado com sucesso!{Style.RESET_ALL}")


def cadastrar_conta(usuarios, contas):
    print(f"{Fore.YELLOW}=== Cadastro de Conta ==={Style.RESET_ALL}")
    cpf = input("Digite o CPF do usuário para vincular a nova conta: ")
    usuario = next((u for u in usuarios if u.cpf == cpf), None)

    if not usuario:
        print(f"{Fore.RED}❌ Usuário não encontrado com o CPF {cpf}.{Style.RESET_ALL}")
        return

    conta = ContaCorrente(cliente=usuario)
    contas.append(conta)
    print(f"{Fore.GREEN}✅ Conta número {conta.numero} cadastrada com sucesso para o usuário {usuario.nome}.{Style.RESET_ALL}")


def selecionar_cliente(usuarios):
    print(f"{Fore.YELLOW}=== Seleção de Cliente ==={Style.RESET_ALL}")
    cpf = input("Digite o CPF do cliente: ")
    cliente = next((u for u in usuarios if u.cpf == cpf), None)

    if not cliente:
        print(f"{Fore.RED}❌ Cliente não encontrado com o CPF {cpf}.{Style.RESET_ALL}")
        return None

    print(f"{Fore.GREEN}✅ Cliente {cliente.nome} selecionado com sucesso!{Style.RESET_ALL}")
    return cliente


def exibir_contas(contas):
    cpf = input("Digite o CPF do usuário para visualizar as contas: ")
    contas_usuario = [c for c in contas if c.cliente.cpf == cpf]

    if not contas_usuario:
        print(f"{Fore.RED}❌ Nenhuma conta encontrada para o CPF {cpf}.{Style.RESET_ALL}")
        return

    print(f"{Fore.YELLOW}📄 Contas do usuário:")
    for c in contas_usuario:
        print(f"Conta número: {c.numero} | Saldo: R${c.saldo:.2f}")


def selecionar_conta(contas, cpf=None):
    if cpf is None:
        cpf = input("Digite o CPF do usuário: ")
    contas_usuario = [c for c in contas if c.cliente.cpf == cpf]

    if not contas_usuario:
        print(f"{Fore.RED}❌ Nenhuma conta encontrada para o CPF {cpf}.{Style.RESET_ALL}")
        return None

    print(f"{Fore.YELLOW}Selecione a conta desejada:")
    for i, c in enumerate(contas_usuario):
        print(f"{i + 1} - Conta número {c.numero} | Saldo: R${c.saldo:.2f}")

    try:
        opcao = int(input(f"{Fore.YELLOW}Digite o número da conta: {Style.RESET_ALL}"))
        return contas_usuario[opcao - 1]
    except (ValueError, IndexError):
        print(f"{Fore.RED}❌ Opção inválida!{Style.RESET_ALL}")
        return None


def realizar_operacao(contas, operacao, cliente_ativo=None):
    cpf = cliente_ativo.cpf if cliente_ativo else None
    conta = selecionar_conta(contas, cpf)
    if not conta:
        return

    try:
        valor = float(input(f"Digite o valor para {operacao}: R$ "))
        if operacao == "depósito":
            conta.depositar(valor)
        elif operacao == "saque":
            conta.sacar(valor)
    except ValueError:
        print(f"{Fore.RED}❌ Valor inválido! Digite um número.{Style.RESET_ALL}")


def exibir_extrato(contas, cliente_ativo=None):
    cpf = cliente_ativo.cpf if cliente_ativo else None
    conta = selecionar_conta(contas, cpf)
    if not conta:
        return

    print(f"{Fore.YELLOW}📄 Extrato da conta {conta.numero}:")
    print(f"Saldo atual: R${conta.saldo:.2f}")
    if not conta.historico.transacoes:
        print(f"{Fore.YELLOW}📄 Extrato está vazio.{Style.RESET_ALL}")
    else:
        for transacao in conta.historico.transacoes:
            tipo = "Saque" if isinstance(transacao, Saque) else "Depósito"
            print(f"{Fore.YELLOW}{tipo}: R${transacao.valor:.2f} ({transacao.data}){Style.RESET_ALL}")


def exibir_menu():
    print(f"{Fore.YELLOW}+--------------------------------------+{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|    Bem-vindo ao Banco GoldSnake!     |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}+--------------------------------------+{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|           MENU PRINCIPAL             |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            1 - Cadastrar Usuário     |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            2 - Cadastrar Conta       |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            3 - Selecionar Cliente    |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            4 - Exibir Contas         |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            5 - Depositar             |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            6 - Sacar                 |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            7 - Exibir Extrato        |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}|            8 - Sair                  |{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}+--------------------------------------+{Style.RESET_ALL}")


def main():
    usuarios, contas = carregar_dados()
    cliente_ativo = None  # Variável para armazenar o cliente selecionado

    while True:
        exibir_menu()
        try:
            opcao = int(input("Digite a opção desejada: "))
        except ValueError:
            print(f"{Fore.RED}❌ Opção inválida! Digite um número.{Style.RESET_ALL}")
            continue

        if opcao == 1:
            cadastrar_usuario(usuarios)
        elif opcao == 2:
            cadastrar_conta(usuarios, contas)
        elif opcao == 3:
            cliente_ativo = selecionar_cliente(usuarios)
        elif opcao == 4:
            exibir_contas(contas)
        elif opcao == 5:
            realizar_operacao(contas, "depósito", cliente_ativo)
        elif opcao == 6:
            realizar_operacao(contas, "saque", cliente_ativo)
        elif opcao == 7:
            exibir_extrato(contas, cliente_ativo)
        elif opcao == 8:
            print(f"{Fore.YELLOW}👋 Obrigado por usar o Banco GoldSnake. Até logo!{Style.RESET_ALL}")
            salvar_dados(usuarios, contas)
            break
        else:
            print(f"{Fore.RED}❌ Opção inválida!{Style.RESET_ALL}")


if __name__ == '__main__':
    main()