import { eq, and, desc, gte, lte } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import {
  InsertUser,
  users,
  categories,
  products,
  sizes,
  flavors,
  cartItems,
  deliveryAddresses,
  orders,
  orderItems,
  loyaltyPoints,
  loyaltyTransactions,
  loyaltyRewards,
  deliveryNeighborhoods,
} from "../drizzle/schema";
import { ENV } from "./_core/env";

let _db: ReturnType<typeof drizzle> | null = null;

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "phone", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = "admin";
      updateSet.role = "admin";
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db
    .select()
    .from(users)
    .where(eq(users.openId, openId))
    .limit(1);

  return result.length > 0 ? result[0] : undefined;
}

// ============ CATEGORIES ============
export async function getCategories() {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(categories)
    .where(eq(categories.isActive, true))
    .orderBy(categories.displayOrder);
}

// ============ PRODUCTS ============
export async function getProductsByCategory(categoryId: number) {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(products)
    .where(and(eq(products.categoryId, categoryId), eq(products.isActive, true)))
    .orderBy(products.displayOrder);
}

export async function getProductById(productId: number) {
  const db = await getDb();
  if (!db) return null;

  const result = await db
    .select()
    .from(products)
    .where(eq(products.id, productId))
    .limit(1);

  return result.length > 0 ? result[0] : null;
}

// ============ SIZES ============
export async function getSizes() {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(sizes)
    .where(eq(sizes.isActive, true))
    .orderBy(sizes.displayOrder);
}

// ============ FLAVORS ============
export async function getFlavors() {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(flavors)
    .where(eq(flavors.isActive, true))
    .orderBy(flavors.displayOrder);
}

// ============ CART ============
export async function getCartItems(userId: number) {
  const db = await getDb();
  if (!db) return [];

  return db.select().from(cartItems).where(eq(cartItems.userId, userId));
}

export async function addToCart(
  userId: number,
  productId: number,
  quantity: number,
  unitPrice: string,
  sizeId?: number,
  selectedFlavors?: number[],
  customizationNotes?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.insert(cartItems).values({
    userId,
    productId,
    quantity,
    unitPrice: unitPrice as any,
    sizeId,
    selectedFlavors: selectedFlavors || [],
    customizationNotes,
  });
}

export async function updateCartItem(
  cartItemId: number,
  quantity: number
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db
    .update(cartItems)
    .set({ quantity })
    .where(eq(cartItems.id, cartItemId));
}

export async function removeFromCart(cartItemId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.delete(cartItems).where(eq(cartItems.id, cartItemId));
}

export async function clearCart(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.delete(cartItems).where(eq(cartItems.userId, userId));
}

// ============ DELIVERY ADDRESSES ============
export async function getDeliveryAddresses(userId: number) {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(deliveryAddresses)
    .where(eq(deliveryAddresses.userId, userId));
}

export async function addDeliveryAddress(
  userId: number,
  street: string,
  number: string,
  neighborhood: string,
  city: string,
  state: string,
  zipCode: string,
  complement?: string,
  isDefault?: boolean
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.insert(deliveryAddresses).values({
    userId,
    street,
    number,
    neighborhood,
    city,
    state,
    zipCode,
    complement,
    isDefault: isDefault || false,
  });
}

// ============ DELIVERY NEIGHBORHOODS ============
export async function getDeliveryNeighborhoods() {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(deliveryNeighborhoods)
    .where(eq(deliveryNeighborhoods.isActive, true));
}

export async function getNeighborhoodByName(name: string) {
  const db = await getDb();
  if (!db) return null;

  const result = await db
    .select()
    .from(deliveryNeighborhoods)
    .where(eq(deliveryNeighborhoods.name, name))
    .limit(1);

  return result.length > 0 ? result[0] : null;
}

// ============ ORDERS ============
export async function createOrder(
  userId: number,
  orderNumber: string,
  deliveryType: "delivery" | "pickup",
  paymentMethod: "cash" | "credit_card" | "debit_card" | "pix" | "voucher",
  subtotal: string,
  deliveryFee: string,
  discount: string,
  total: string,
  deliveryAddressId?: number,
  estimatedDeliveryTime?: number,
  notes?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(orders).values({
    userId,
    orderNumber,
    deliveryType,
    paymentMethod,
    subtotal: subtotal as any,
    deliveryFee: deliveryFee as any,
    discount: discount as any,
    total: total as any,
    deliveryAddressId,
    estimatedDeliveryTime,
    notes,
  });

  return result;
}

export async function getOrderById(orderId: number) {
  const db = await getDb();
  if (!db) return null;

  const result = await db
    .select()
    .from(orders)
    .where(eq(orders.id, orderId))
    .limit(1);

  return result.length > 0 ? result[0] : null;
}

export async function getUserOrders(userId: number) {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(orders)
    .where(eq(orders.userId, userId))
    .orderBy(desc(orders.createdAt));
}

export async function updateOrderStatus(
  orderId: number,
  status: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.update(orders).set({ status: status as any }).where(eq(orders.id, orderId));
}

// ============ ORDER ITEMS ============
export async function addOrderItem(
  orderId: number,
  productId: number,
  quantity: number,
  unitPrice: string,
  subtotal: string,
  sizeId?: number,
  selectedFlavors?: number[],
  customizationNotes?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.insert(orderItems).values({
    orderId,
    productId,
    quantity,
    unitPrice: unitPrice as any,
    subtotal: subtotal as any,
    sizeId,
    selectedFlavors: selectedFlavors || [],
    customizationNotes,
  });
}

export async function getOrderItems(orderId: number) {
  const db = await getDb();
  if (!db) return [];

  return db.select().from(orderItems).where(eq(orderItems.orderId, orderId));
}

// ============ LOYALTY POINTS ============
export async function getLoyaltyPoints(userId: number) {
  const db = await getDb();
  if (!db) return null;

  const result = await db
    .select()
    .from(loyaltyPoints)
    .where(eq(loyaltyPoints.userId, userId))
    .limit(1);

  return result.length > 0 ? result[0] : null;
}

export async function createLoyaltyPoints(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return db.insert(loyaltyPoints).values({
    userId,
    totalPoints: 0,
    availablePoints: 0,
  });
}

export async function addLoyaltyPoints(
  userId: number,
  points: number,
  orderId?: number,
  description?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  // Get current points
  const current = await getLoyaltyPoints(userId);
  if (!current) {
    await createLoyaltyPoints(userId);
  }

  const newTotal = (current?.totalPoints || 0) + points;
  const newAvailable = (current?.availablePoints || 0) + points;

  // Update loyalty points
  await db
    .update(loyaltyPoints)
    .set({
      totalPoints: newTotal,
      availablePoints: newAvailable,
    })
    .where(eq(loyaltyPoints.userId, userId));

  // Record transaction
  return db.insert(loyaltyTransactions).values({
    userId,
    orderId,
    type: "earned",
    points,
    description,
  });
}

export async function redeemLoyaltyPoints(
  userId: number,
  points: number,
  description?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  // Get current points
  const current = await getLoyaltyPoints(userId);
  if (!current) {
    throw new Error("User loyalty points not found");
  }

  if (current.availablePoints < points) {
    throw new Error("Insufficient loyalty points");
  }

  const newAvailable = current.availablePoints - points;

  // Update loyalty points
  await db
    .update(loyaltyPoints)
    .set({
      availablePoints: newAvailable,
    })
    .where(eq(loyaltyPoints.userId, userId));

  // Record transaction
  return db.insert(loyaltyTransactions).values({
    userId,
    type: "redeemed",
    points,
    description,
  });
}

// ============ LOYALTY REWARDS ============
export async function getLoyaltyRewards() {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(loyaltyRewards)
    .where(eq(loyaltyRewards.isActive, true))
    .orderBy(loyaltyRewards.displayOrder);
}

export async function getRewardById(rewardId: number) {
  const db = await getDb();
  if (!db) return null;

  const result = await db
    .select()
    .from(loyaltyRewards)
    .where(eq(loyaltyRewards.id, rewardId))
    .limit(1);

  return result.length > 0 ? result[0] : null;
}
