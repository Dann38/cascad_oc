class HypProblem:
    def __init__(self, T, S, C, B, F, G, X0, Y0, phi_dx, phi_dy) -> None:
        self.set_T(T)
        self.set_S(S)
        self.set_C(C)
        self.set_B(B)
        self.set_F(F)
        self.set_G(G)
        self.set_X0(X0)
        self.set_Y0(Y0)
        self.set_phi_dx(phi_dx)
        self.set_phi_dy(phi_dy)

    def set_T(self, T):
        self.T0 = T[0]
        self.T1 = T[1]


    def set_S(self, S):
        self.S0 = S[0]
        self.S1 = S[1]

    def set_C(self, C):
        self.C1 = C[0]
        self.C2 = C[1]

    def set_B(self, B):
        self.B11 = B[0][0]
        self.B12 = B[0][1]
        self.B21 = B[1][0]
        self.B22 = B[1][1]

    def set_F(self, F):
        self.F1 = F[0]
        self.F2 = F[1]

    def set_G(self, G):
        self.G11 = G[0][0]
        self.G12 = G[0][1]
        self.G21 = G[1][0]
        self.G22 = G[1][1]

    def set_X0(self, X0):
        self.x0 = X0

    def set_Y0(self, Y0):
        self.y0 = Y0

    def set_phi_dx(self, phi_dx):
        self.phi_dx = phi_dx

    def set_phi_dy(self, phi_dy):
        self.phi_dy = phi_dy