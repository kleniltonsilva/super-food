import { z } from "zod";
import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, protectedProcedure, router } from "./_core/trpc";
import * as db from "./db";
import { nanoid } from "nanoid";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query((opts) => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  // ============ MENU ROUTES ============
  menu: router({
    getCategories: publicProcedure.query(async () => {
      return db.getCategories();
    }),

    getProductsByCategory: publicProcedure
      .input(z.object({ categoryId: z.number() }))
      .query(async ({ input }) => {
        return db.getProductsByCategory(input.categoryId);
      }),

    getProductById: publicProcedure
      .input(z.object({ productId: z.number() }))
      .query(async ({ input }) => {
        return db.getProductById(input.productId);
      }),

    getSizes: publicProcedure.query(async () => {
      return db.getSizes();
    }),

    getFlavors: publicProcedure.query(async () => {
      return db.getFlavors();
    }),
  }),

  // ============ CART ROUTES ============
  cart: router({
    getItems: protectedProcedure.query(async ({ ctx }) => {
      return db.getCartItems(ctx.user.id);
    }),

    addItem: protectedProcedure
      .input(
        z.object({
          productId: z.number(),
          quantity: z.number().min(1),
          unitPrice: z.string(),
          sizeId: z.number().optional(),
          selectedFlavors: z.array(z.number()).optional(),
          customizationNotes: z.string().optional(),
        })
      )
      .mutation(async ({ ctx, input }) => {
        return db.addToCart(
          ctx.user.id,
          input.productId,
          input.quantity,
          input.unitPrice,
          input.sizeId,
          input.selectedFlavors,
          input.customizationNotes
        );
      }),

    updateItem: protectedProcedure
      .input(
        z.object({
          cartItemId: z.number(),
          quantity: z.number().min(1),
        })
      )
      .mutation(async ({ input }) => {
        return db.updateCartItem(input.cartItemId, input.quantity);
      }),

    removeItem: protectedProcedure
      .input(z.object({ cartItemId: z.number() }))
      .mutation(async ({ input }) => {
        return db.removeFromCart(input.cartItemId);
      }),

    clear: protectedProcedure.mutation(async ({ ctx }) => {
      return db.clearCart(ctx.user.id);
    }),
  }),

  // ============ DELIVERY ROUTES ============
  delivery: router({
    getAddresses: protectedProcedure.query(async ({ ctx }) => {
      return db.getDeliveryAddresses(ctx.user.id);
    }),

    addAddress: protectedProcedure
      .input(
        z.object({
          street: z.string().min(1),
          number: z.string().min(1),
          neighborhood: z.string().min(1),
          city: z.string().min(1),
          state: z.string().min(2).max(2),
          zipCode: z.string().min(1),
          complement: z.string().optional(),
          isDefault: z.boolean().optional(),
        })
      )
      .mutation(async ({ ctx, input }) => {
        return db.addDeliveryAddress(
          ctx.user.id,
          input.street,
          input.number,
          input.neighborhood,
          input.city,
          input.state,
          input.zipCode,
          input.complement,
          input.isDefault
        );
      }),

    getNeighborhoods: publicProcedure.query(async () => {
      return db.getDeliveryNeighborhoods();
    }),

    getNeighborhoodByName: publicProcedure
      .input(z.object({ name: z.string() }))
      .query(async ({ input }) => {
        return db.getNeighborhoodByName(input.name);
      }),
  }),

  // ============ ORDERS ROUTES ============
  orders: router({
    create: protectedProcedure
      .input(
        z.object({
          deliveryType: z.enum(["delivery", "pickup"]),
          paymentMethod: z.enum([
            "cash",
            "credit_card",
            "debit_card",
            "pix",
            "voucher",
          ]),
          subtotal: z.string(),
          deliveryFee: z.string(),
          discount: z.string(),
          total: z.string(),
          deliveryAddressId: z.number().optional(),
          estimatedDeliveryTime: z.number().optional(),
          notes: z.string().optional(),
          items: z.array(
            z.object({
              productId: z.number(),
              quantity: z.number(),
              unitPrice: z.string(),
              subtotal: z.string(),
              sizeId: z.number().optional(),
              selectedFlavors: z.array(z.number()).optional(),
              customizationNotes: z.string().optional(),
            })
          ),
        })
      )
      .mutation(async ({ ctx, input }) => {
        const orderNumber = `ORD-${Date.now()}-${nanoid(6)}`;

        // Create order
        const orderResult = await db.createOrder(
          ctx.user.id,
          orderNumber,
          input.deliveryType,
          input.paymentMethod,
          input.subtotal,
          input.deliveryFee,
          input.discount,
          input.total,
          input.deliveryAddressId,
          input.estimatedDeliveryTime,
          input.notes
        );

        // Get the inserted order ID
        const orderId = (orderResult as any).insertId;

        // Add order items
        for (const item of input.items) {
          await db.addOrderItem(
            orderId,
            item.productId,
            item.quantity,
            item.unitPrice,
            item.subtotal,
            item.sizeId,
            item.selectedFlavors,
            item.customizationNotes
          );
        }

        // Add loyalty points (1 point per real spent)
        const pointsToAdd = Math.floor(parseFloat(input.subtotal));
        if (pointsToAdd > 0) {
          await db.addLoyaltyPoints(
            ctx.user.id,
            pointsToAdd,
            orderId,
            `Pontos ganhos do pedido ${orderNumber}`
          );
        }

        // Clear cart
        await db.clearCart(ctx.user.id);

        // Notify owner
        try {
          const { notifyOwner } = await import("./_core/notification");
          await notifyOwner({
            title: "Novo Pedido Recebido",
            content: `Novo pedido #${orderNumber} de R$ ${input.total} foi realizado!`,
          });
        } catch (error) {
          console.error("Failed to notify owner:", error);
        }

        return {
          orderId,
          orderNumber,
          success: true,
        };
      }),

    getById: protectedProcedure
      .input(z.object({ orderId: z.number() }))
      .query(async ({ input }) => {
        const order = await db.getOrderById(input.orderId);
        if (!order) return null;

        const items = await db.getOrderItems(input.orderId);
        return { ...order, items };
      }),

    getUserOrders: protectedProcedure.query(async ({ ctx }) => {
      return db.getUserOrders(ctx.user.id);
    }),

    updateStatus: protectedProcedure
      .input(
        z.object({
          orderId: z.number(),
          status: z.enum([
            "pending",
            "confirmed",
            "preparing",
            "ready",
            "delivering",
            "delivered",
            "cancelled",
          ]),
        })
      )
      .mutation(async ({ ctx, input }) => {
        // Check if user is admin or owner of the order
        const order = await db.getOrderById(input.orderId);
        if (!order) throw new Error("Order not found");

        if (ctx.user.role !== "admin" && order.userId !== ctx.user.id) {
          throw new Error("Unauthorized");
        }

        return db.updateOrderStatus(input.orderId, input.status);
      }),
  }),

  // ============ LOYALTY ROUTES ============
  loyalty: router({
    getPoints: protectedProcedure.query(async ({ ctx }) => {
      let points = await db.getLoyaltyPoints(ctx.user.id);
      if (!points) {
        await db.createLoyaltyPoints(ctx.user.id);
        points = await db.getLoyaltyPoints(ctx.user.id);
      }
      return points;
    }),

    getRewards: publicProcedure.query(async () => {
      return db.getLoyaltyRewards();
    }),

    redeemReward: protectedProcedure
      .input(z.object({ rewardId: z.number() }))
      .mutation(async ({ ctx, input }) => {
        const reward = await db.getRewardById(input.rewardId);
        if (!reward) throw new Error("Reward not found");

        const points = await db.getLoyaltyPoints(ctx.user.id);
        if (!points || points.availablePoints < reward.pointsCost) {
          throw new Error("Insufficient loyalty points");
        }

        await db.redeemLoyaltyPoints(
          ctx.user.id,
          reward.pointsCost,
          `Resgate do prêmio: ${reward.name}`
        );

        return {
          success: true,
          reward,
        };
      }),
  }),
});

export type AppRouter = typeof appRouter;
